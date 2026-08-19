#!/usr/bin/env python3
"""Rebuild RepresentativeDomains and Proteins.protein_interpro_id, and nothing else.

Standalone: copy this one file plus the three source files to the target machine.
It does not import from DoChaP-db, so it can run without the rest of the repo.

WHY THIS EXISTS
---------------
`Proteins.protein_interpro_id` (which despite its name holds a UniProt accession)
was populated by reading columns 3 and 19 of idmapping_selected.tab as single
values. They are "; "-separated LISTS. One accession routinely names many
transcripts - P08575 (CD45) lists 16 RefSeq proteins and 9 Ensembl transcripts on
one line - so every id but the first was silently dropped. That left 31% of
canonical transcripts with no accession and therefore NO DOMAINS AT ALL, because
the domain load gates on membership of that column. Full write-up in
DoChaP-db/UNIPROT_MAPPING_LOSES_CANONICALS.md.

This script carries the fixed logic: both columns are split, every id is
recorded, and where two accessions name the same protein the REVIEWED
(Swiss-Prot) one wins - identified from column 1, whose mnemonic begins with the
accession only for unreviewed entries.

WHAT IT TOUCHES
---------------
  Proteins.protein_interpro_id     reset to NULL, then repopulated
  RepresentativeDomains            emptied, then repopulated
Nothing else is read for writing. Every other table and column is left alone.

SOURCE FILES (same release - do not mix)
---------------------------------------
  idmapping_selected.tab.gz   UniProt      ftp.ebi.ac.uk/pub/databases/uniprot/
                                           current_release/knowledgebase/idmapping/
  match_complete.xml.gz       InterPro     ftp.ebi.ac.uk/pub/databases/interpro/
  interpro.xml.gz             InterPro     current_release/

USAGE
-----
  python3 rebuild_representative_domains.py \
      --db /path/to/DB_merged.sqlite \
      --idmapping /path/to/idmapping_selected.tab.gz \
      --matches   /path/to/match_complete.xml.gz \
      --entries   /path/to/interpro.xml.gz \
      --backup    /path/to/DB_merged.sqlite.bak \
      --yes

  --step mapping   only rewrite Proteins.protein_interpro_id  (~20-40 min)
  --step domains   only rewrite RepresentativeDomains         (~2-5 h)
  --step both      default

Run --step mapping first if you want to check the coverage numbers before
committing to the long InterPro pass; --step domains reads the accessions back
out of the database, so the two can be run in separate sessions.

Requires: lxml. pandas is used if present but is not required (--no-pandas).
"""
import os
# MUST run before anything imports numpy. On a cluster node OpenBLAS sizes its
# thread pool from the machine's core count (72 here) while the per-user process
# limit applies, and numpy dies at import with "blas_thread_init: pthread_create
# failed". This script does no linear algebra at all, so one thread is plenty.
# RepresentativeDomainsBuilder.py carries the same guard for the same reason.
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
             "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import collections
import gzip
import shutil
import sqlite3
import sys
import time

try:
    from lxml import etree
except ImportError as exc:                                    # pragma: no cover
    sys.exit(f"missing dependency: {exc}. lxml is required.")

# pandas is optional: it only ever reads the TSV. If it is missing - or if numpy
# cannot start on this node despite the guard above - fall back to plain gzip.
try:
    import pandas as pd
except Exception as _exc:                                     # noqa: BLE001
    pd = None
    _PANDAS_ERROR = _exc

COLLISION_STRATEGIES = ("ensembl", "refseq", "ignore")
# A known case used as a self-check: this transcript is SECOND in P08575's list
# and was the one the old code could not reach.
CANARY_TRANSCRIPT, CANARY_ACCESSION = "ENST00000442510", "P08575"


# ── the fix ───────────────────────────────────────────────────────────────────
def split_ids(field):
    """idmapping's RefSeq and Ensembl columns hold "; "-separated lists."""
    if not field:
        return ()
    return tuple(p.strip() for p in field.split(';') if p.strip())


def claim(hits, pair, accession, reviewed):
    """Record `accession` for `pair`, preferring a reviewed entry.

    A reviewed entry displaces an unreviewed one; between two of equal status the
    first seen wins, so the result does not depend on where pandas splits chunks.
    """
    previous = hits.get(pair)
    if previous is None or (reviewed and not previous[1]):
        hits[pair] = (accession, reviewed)


# ── reading the mapping file ──────────────────────────────────────────────────
# Only lines naming a RefSeq protein or an Ensembl transcript can match anything
# in Proteins, and most of UniProt names neither. Checking that as a substring
# before splitting 22 columns skips the majority for the cost of a few memchrs.
# Prefixes taken from the database itself: NP_/XP_/YP_ and ENS*T.
_INTERESTING = ("ENS", "NP_", "XP_", "YP_")


def _rows_plain(path):
    """(accession, uniprot_id, refseq_field, enst_field) with no numpy anywhere."""
    with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if not any(tag in line for tag in _INTERESTING):
                continue
            f = line.rstrip('\n').split('\t', 20)
            if len(f) <= 19:
                continue
            yield f[0], f[1], f[3], f[19]


def _rows_pandas(path, chunksize):
    reader = pd.read_csv(path, sep='\t', header=None, usecols=[0, 1, 3, 19],
                         dtype=str, na_filter=False, chunksize=chunksize,
                         compression='gzip', engine='c')
    for chunk in reader:
        for row in chunk.itertuples(index=False, name=None):
            yield row


# ── step 1: Proteins.protein_interpro_id ──────────────────────────────────────
def rewrite_protein_mapping(cur, mapping_path, collision_strategy="ensembl",
                            chunksize=1_000_000, force_plain=False):
    print("\n=== STEP 1: Proteins.protein_interpro_id ===", flush=True)
    rows = cur.execute("SELECT protein_refseq_id, protein_ensembl_id, "
                       "transcript_ensembl_id FROM Proteins;").fetchall()
    refseq_to_pair, enst_to_pair = {}, {}
    for refseq_id, ensembl_id, transcript_id in rows:
        pair = (refseq_id, ensembl_id)
        if refseq_id:
            refseq_to_pair[refseq_id] = pair
        if transcript_id:
            enst_to_pair[transcript_id] = pair
            bare = transcript_id.split('.')[0]
            if bare != transcript_id:
                enst_to_pair.setdefault(bare, pair)
    print(f"  {len(rows):,} protein rows "
          f"({len(refseq_to_pair):,} refseq keys, {len(enst_to_pair):,} transcript keys)",
          flush=True)

    refseq_hits, ensembl_hits, scanned = {}, {}, 0
    t0 = time.time()
    if pd is not None and not force_plain:
        print("  reading with pandas", flush=True)
        source = _rows_pandas(mapping_path, chunksize)
    else:
        why = "forced" if force_plain else f"pandas unavailable ({_PANDAS_ERROR})"
        print(f"  reading with the plain gzip reader ({why})", flush=True)
        source = _rows_plain(mapping_path)

    for accession, uniprot_id, refseq_field, enst_field in source:
        scanned += 1
        if scanned % 10_000_000 == 0:
            print(f"  scanned {scanned:,} lines ({time.time()-t0:.0f}s), "
                  f"{len(ensembl_hits):,} transcripts matched", flush=True)
        if True:
            # reviewed entries carry a mnemonic (PTPRC_HUMAN); unreviewed ones
            # repeat their accession (A0A2R8Y5B1_HUMAN).
            reviewed = bool(uniprot_id) and not uniprot_id.startswith(accession)
            for refseq_id in split_ids(refseq_field):
                pair = refseq_to_pair.get(refseq_id)
                if pair is not None:
                    claim(refseq_hits, pair, accession, reviewed)
            for enst_id in split_ids(enst_field):
                # versioned first, then bare: a fallback for ONE id, which is why
                # it must not also terminate the loop over the list.
                pair = enst_to_pair.get(enst_id) or enst_to_pair.get(enst_id.split('.')[0])
                if pair is not None:
                    claim(ensembl_hits, pair, accession, reviewed)
    print(f"  scan complete in {time.time()-t0:.0f}s: "
          f"{len(refseq_hits):,} refseq hits, {len(ensembl_hits):,} ensembl hits", flush=True)

    resolved, collisions, reviewed_wins = {}, 0, 0
    for pair in set(refseq_hits) | set(ensembl_hits):
        r_id, r_rev = refseq_hits.get(pair, (None, False))
        e_id, e_rev = ensembl_hits.get(pair, (None, False))
        if r_id and e_id and r_id != e_id:
            if r_rev != e_rev:
                reviewed_wins += 1
                resolved[pair] = r_id if r_rev else e_id
                continue
            collisions += 1
            if collision_strategy == "ignore":
                continue
            resolved[pair] = r_id if collision_strategy == "refseq" else e_id
        else:
            resolved[pair] = r_id or e_id
    if reviewed_wins:
        print(f"  {reviewed_wins:,} branch disagreements settled by preferring the reviewed entry")
    if collisions:
        print(f"  {collisions:,} same-status collisions (strategy='{collision_strategy}')")

    per_acc = collections.Counter(resolved.values())
    shared = sum(1 for n in per_acc.values() if n > 1)
    print(f"  {len(per_acc):,} distinct accessions over {len(resolved):,} proteins; "
          f"{shared:,} cover more than one transcript", flush=True)

    print("  writing...", flush=True)
    cur.execute("UPDATE Proteins SET protein_interpro_id = NULL;")
    cur.executemany("UPDATE Proteins SET protein_interpro_id = ? "
                    "WHERE protein_refseq_id IS ? AND protein_ensembl_id IS ?;",
                    [(acc, rs, ens) for (rs, ens), acc in resolved.items()])
    print(f"  Proteins.protein_interpro_id set for {len(resolved):,} rows", flush=True)


# ── step 2: RepresentativeDomains ─────────────────────────────────────────────
def parse_interpro_entries(path):
    print("\n  parsing interpro.xml.gz for entry types + descriptions...", flush=True)
    t0, entries = time.time(), {}
    for _, entry in etree.iterparse(gzip.open(path, 'rb'), events=('end',), tag='interpro'):
        ipr_id = entry.get('id')
        if ipr_id:
            abstract = entry.find('abstract')
            text = None
            if abstract is not None:
                text = ' '.join(' '.join(abstract.itertext()).split()) or None
            entries[ipr_id] = (entry.get('type'), text)
        entry.clear()
        while entry.getprevious() is not None:
            del entry.getparent()[0]
    print(f"  {len(entries):,} InterPro entries ({time.time()-t0:.0f}s)", flush=True)
    return entries


def rebuild_domains(cur, matches_path, entries_path, batch_size=500_000):
    print("\n=== STEP 2: RepresentativeDomains ===", flush=True)
    entry_meta = parse_interpro_entries(entries_path)

    known = {r[0] for r in cur.execute(
        "SELECT DISTINCT protein_interpro_id FROM Proteins "
        "WHERE protein_interpro_id IS NOT NULL AND protein_interpro_id != '';")}
    print(f"  {len(known):,} accessions to retain", flush=True)
    if not known:
        sys.exit("  ABORT: no accessions in Proteins - run --step mapping first.")

    cur.execute("DELETE FROM RepresentativeDomains;")
    insert = ("INSERT INTO RepresentativeDomains (protein_interpro_id, domain_id, "
              "domain_name, start, end, score, description, type) VALUES (?,?,?,?,?,?,?,?)")

    t0, batch, total, seen, kept = time.time(), [], 0, 0, 0
    for _, protein in etree.iterparse(gzip.open(matches_path, 'rb'),
                                      events=('end',), tag='protein'):
        seen += 1
        pid = protein.get('id')
        if pid in known:
            kept += 1
            for match in protein.findall('match'):
                ipr = match.find('ipr')
                ipr_id = ipr.get('id') if ipr is not None else match.get('id')
                ipr_name = ipr.get('name') if ipr is not None else match.get('name')
                for lcn in match.findall('lcn'):
                    if lcn.get('representative') != 'true':
                        continue
                    score = lcn.get('score')
                    etype, description = entry_meta.get(ipr_id, (None, None))
                    batch.append((pid, ipr_id, ipr_name, int(lcn.get('start')),
                                  int(lcn.get('end')), float(score) if score else None,
                                  description, etype))
        protein.clear()
        while protein.getprevious() is not None:
            del protein.getparent()[0]
        if len(batch) >= batch_size:
            cur.executemany(insert, batch); total += len(batch); batch = []
            print(f"  {seen:,} proteins read, {kept:,} kept, {total:,} rows "
                  f"({time.time()-t0:.0f}s)", flush=True)
    if batch:
        cur.executemany(insert, batch); total += len(batch)
    print(f"  done: {seen:,} proteins read, {kept:,} matched, {total:,} domain rows "
          f"({time.time()-t0:.0f}s)", flush=True)


# ── plumbing ──────────────────────────────────────────────────────────────────
def ensure_schema(cur):
    cur.execute("""CREATE TABLE IF NOT EXISTS RepresentativeDomains (
        protein_interpro_id TEXT, domain_id TEXT, domain_name TEXT,
        start INTEGER, end INTEGER, score REAL, description TEXT, type TEXT);""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rep_domains_prot "
                "ON RepresentativeDomains(protein_interpro_id);")
    cols = {r[1] for r in cur.execute("PRAGMA table_info(Proteins);")}
    if not cols:
        sys.exit("ABORT: no Proteins table - is this a DoChaP database?")
    if "protein_interpro_id" not in cols:
        cur.execute("ALTER TABLE Proteins ADD COLUMN protein_interpro_id TEXT;")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_proteins_interpro "
                    "ON Proteins(protein_interpro_id);")


def stats(cur):
    d = cur.execute("SELECT COUNT(*) FROM RepresentativeDomains;").fetchone()[0]
    a = cur.execute("SELECT COUNT(*) FROM Proteins WHERE protein_interpro_id IS NOT NULL "
                    "AND protein_interpro_id != '';").fetchone()[0]
    n = cur.execute("SELECT COUNT(*) FROM Proteins;").fetchone()[0]
    canary = cur.execute("SELECT protein_interpro_id FROM Proteins "
                         "WHERE transcript_ensembl_id LIKE ?||'%';",
                         (CANARY_TRANSCRIPT,)).fetchone()
    return dict(domain_rows=d, with_accession=a, proteins=n,
                canary=canary[0] if canary else "(transcript absent)")


def show(label, s):
    print(f"  {label:8s} RepresentativeDomains rows : {s['domain_rows']:,}")
    print(f"  {'':8s} proteins with an accession  : {s['with_accession']:,} of {s['proteins']:,} "
          f"({100*s['with_accession']/max(s['proteins'],1):.1f}%)")
    print(f"  {'':8s} {CANARY_TRANSCRIPT} -> {s['canary']}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--db', required=True)
    p.add_argument('--idmapping')
    p.add_argument('--matches')
    p.add_argument('--entries')
    p.add_argument('--step', choices=('mapping', 'domains', 'both'), default='both')
    p.add_argument('--collision-strategy', choices=COLLISION_STRATEGIES, default='ensembl')
    p.add_argument('--backup', help='copy the database here before touching it')
    p.add_argument('--fast', action='store_true',
                   help='synchronous=OFF and an in-memory journal: faster, but a crash '
                        'or power loss can corrupt the database. Use only with --backup.')
    p.add_argument('--no-pandas', action='store_true',
                   help='read the mapping file with plain gzip instead of pandas. '
                        'Use on a node where numpy will not import; it is a little '
                        'slower but needs no numpy at all.')
    p.add_argument('--yes', action='store_true', help='required to write anything')
    a = p.parse_args()

    need = {'mapping': ['idmapping'], 'domains': ['matches', 'entries'],
            'both': ['idmapping', 'matches', 'entries']}[a.step]
    for opt in need:
        if not getattr(a, opt):
            p.error(f"--step {a.step} requires --{opt}")
        if not os.path.exists(getattr(a, opt)):
            p.error(f"--{opt}: no such file: {getattr(a, opt)}")
    if not os.path.exists(a.db):
        p.error(f"--db: no such file: {a.db}")

    print(f"database : {a.db} ({os.path.getsize(a.db)/2**30:.2f} GiB)")
    print(f"step     : {a.step}")
    print("writes   : Proteins.protein_interpro_id and RepresentativeDomains ONLY\n")
    if not a.yes:
        sys.exit("Nothing done. Re-run with --yes to write.")

    if a.backup:
        print(f"backing up to {a.backup} ...", flush=True)
        t0 = time.time(); shutil.copy2(a.db, a.backup)
        print(f"  done ({time.time()-t0:.0f}s)\n", flush=True)
    elif a.fast:
        sys.exit("--fast without --backup is refused: a crash could corrupt the database.")

    con = sqlite3.connect(a.db)
    cur = con.cursor()
    cur.execute("PRAGMA temp_store = MEMORY;")
    cur.execute("PRAGMA cache_size = -2000000;")
    if a.fast:
        cur.execute("PRAGMA synchronous = OFF;")
        cur.execute("PRAGMA journal_mode = MEMORY;")

    ensure_schema(cur)
    before = stats(cur)
    print("BEFORE"); show('', before); print()

    started = time.time()
    if a.step in ('mapping', 'both'):
        rewrite_protein_mapping(cur, a.idmapping, a.collision_strategy,
                                force_plain=a.no_pandas)
        con.commit()
    if a.step in ('domains', 'both'):
        rebuild_domains(cur, a.matches, a.entries)
        con.commit()

    after = stats(cur)
    print(f"\nAFTER  (total {(time.time()-started)/60:.0f} min)"); show('', after)
    print("\nchange")
    print(f"  domain rows        {before['domain_rows']:>12,} -> {after['domain_rows']:>12,}")
    print(f"  with an accession  {before['with_accession']:>12,} -> {after['with_accession']:>12,}")
    print(f"  {CANARY_TRANSCRIPT}  {before['canary']} -> {after['canary']}")
    if a.step in ('mapping', 'both'):
        if after['canary'] == CANARY_ACCESSION:
            print(f"\n  SELF-CHECK PASSED: the canonical PTPRC transcript now carries "
                  f"{CANARY_ACCESSION}.")
        else:
            print(f"\n  SELF-CHECK FAILED: expected {CANARY_ACCESSION}, got {after['canary']!r}. "
                  f"Human data expected; if this is another species, ignore.")
    con.close()
    print("\nDone. No other table was modified.")


if __name__ == '__main__':
    main()
