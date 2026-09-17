import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

import collections
import gzip
import re
import sqlite3
import sys
import threading
import queue
import time
from lxml import etree
import pandas as pd

sys.path.append(os.getcwd())
from Director import SourceBuilder
from httpsDownload import httpsDownload

# --- CONFIGURATION ---
DB_NAME = "DB_merged.sqlite"

UNIPROT_FTP_ADDRESS = "ftp.ebi.ac.uk"
UNIPROT_FTP_PATH = "/pub/databases/uniprot/current_release/knowledgebase/idmapping"
INTERPRO_FTP_ADDRESS = "ftp.ebi.ac.uk"
INTERPRO_FTP_PATH = "/pub/databases/interpro/current_release"

UNIPROT_LOCAL_PATH = "data"
UNIPROT_FILE_NAME  = "idmapping_selected.tab.gz"
INTERPRO_LOCAL_PATH = "data"
INTERPRO_FILE_NAME  = "match_complete.xml.gz"
# Curated InterPro entry metadata (names + <abstract> descriptions), one entry
# per InterPro accession. Lives next to match_complete.xml.gz on the same FTP.
INTERPRO_ENTRIES_FILE_NAME = "interpro.xml.gz"

# Swiss-Prot flat file. idmapping_selected.tab lists a reviewed accession's
# transcripts as ONE flat "; "-separated field with no isoform qualifier -
# Q96P48 (ARAP1) names seven ENSTs there and says nothing about which of its
# seven isoforms each one encodes. The flat file keeps that qualifier on every
# cross-reference:
#
#   DR   Ensembl; ENST00000393609.8; ENSP00000377233.3; ENSG00000186635.17. [Q96P48-6]
#   DR   Ensembl; ENST00000334211.12; ENSP00000335506.8; ENSG00000186635.17. [Q96P48-4]
#
# and states which isoform carries the entry's displayed sequence. That is the
# only thing that separates a transcript whose protein IS this accession's
# sequence from one that merely belongs to the same gene - see
# populate_isoform_flags(). TrEMBL is not needed: its entries are
# isoform-specific and carry no ALTERNATIVE PRODUCTS, so they cannot collide.
UNIPROT_FLATFILE_FTP_PATH = "/pub/databases/uniprot/current_release/knowledgebase/complete"
UNIPROT_FLATFILE_NAME = "uniprot_sprot.dat.gz"

UNIPROT_FILE  = f"{UNIPROT_LOCAL_PATH}/{UNIPROT_FILE_NAME}"
UNIPROT_FLATFILE = f"{UNIPROT_LOCAL_PATH}/{UNIPROT_FLATFILE_NAME}"
INTERPRO_FILE = f"{INTERPRO_LOCAL_PATH}/{INTERPRO_FILE_NAME}"
INTERPRO_ENTRIES_FILE = f"{INTERPRO_LOCAL_PATH}/{INTERPRO_ENTRIES_FILE_NAME}"

COLLISION_STRATEGIES = ("ensembl", "refseq", "ignore")


def download_file(ftp_address, ftp_path, local_dir, file_name):
    # httpsDownload mirrors ftpDownload: it appends ".gz" to the remote name and,
    # with extract=False, leaves the gzipped file on disk. So strip the ".gz"
    # from the remote/local name we hand it - the file still lands at
    # <local_dir>/<file_name> (e.g. data/match_complete.xml.gz), which is what
    # the parser reads.
    base_name = file_name[:-3] if file_name.endswith('.gz') else file_name
    http = httpsDownload('', ftp_address, ftp_path, savePath=local_dir,
                         files2Download=[[base_name, base_name]])
    http.Download(extract=False)


def create_representative_domains_table(cursor):
    """Adds RepresentativeDomains table and protein_interpro_id column to the DoChaP DB."""
    print("Creating RepresentativeDomains table and extending Proteins table...")

    cursor.execute("PRAGMA page_size = 65536;")
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")
    cursor.execute("PRAGMA cache_size = -2000000;")   # ~2 GB RAM cache
    cursor.execute("PRAGMA mmap_size = 10000000000;") # 10 GB memory-mapped I/O
    cursor.execute("PRAGMA temp_store = MEMORY;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RepresentativeDomains (
            protein_interpro_id TEXT,
            domain_id TEXT,
            domain_name TEXT,
            start INTEGER,
            end INTEGER,
            score REAL,
            description TEXT,
            type TEXT
        );
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rep_domains_prot ON RepresentativeDomains(protein_interpro_id);"
    )

    # Handle a RepresentativeDomains table created before the description/type
    # columns existed (mirrors the Proteins.protein_interpro_id guard below).
    rep_cols = {row[1] for row in cursor.execute("PRAGMA table_info(RepresentativeDomains);")}
    if "description" not in rep_cols:
        cursor.execute("ALTER TABLE RepresentativeDomains ADD COLUMN description TEXT;")
    if "type" not in rep_cols:
        cursor.execute("ALTER TABLE RepresentativeDomains ADD COLUMN type TEXT;")

    existing = {row[1] for row in cursor.execute("PRAGMA table_info(Proteins);")}
    if "protein_interpro_id" not in existing:
        cursor.execute("ALTER TABLE Proteins ADD COLUMN protein_interpro_id TEXT;")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_proteins_interpro ON Proteins(protein_interpro_id);"
        )

    # Which UniProt ISOFORM this protein is (e.g. 'Q96P48-4'), and whether the
    # RepresentativeDomains rows filed under its protein_interpro_id actually
    # describe THIS protein's sequence. See populate_isoform_flags().
    if "protein_uniprot_isoform" not in existing:
        cursor.execute("ALTER TABLE Proteins ADD COLUMN protein_uniprot_isoform TEXT;")
    if "interpro_domains_are_own" not in existing:
        cursor.execute("ALTER TABLE Proteins ADD COLUMN interpro_domains_are_own INTEGER;")


def isoform_flags_built(cursor):
    """True if the isoform step has already run against this database.

    Checked separately from representative_domains_built(): a database built
    before this step existed has the domain table but none of the isoform
    verdicts, and must not be reported as complete. The column existing is not
    enough - create_representative_domains_table() adds it to any database it
    touches - so this asks whether any verdict was actually recorded.
    """
    columns = {row[1] for row in cursor.execute("PRAGMA table_info(Proteins);")}
    if "interpro_domains_are_own" not in columns:
        return False
    cursor.execute("SELECT 1 FROM Proteins WHERE interpro_domains_are_own IS NOT NULL LIMIT 1;")
    return cursor.fetchone() is not None


def require_input_files(*paths):
    """Fail before the build starts if an input is missing.

    The InterPro parse takes tens of minutes on a full database, and the isoform
    step runs after it. Discovering a missing download at that point wastes the
    whole run, so every file the build will read is checked up front.
    """
    missing = [path for path in paths if not os.path.exists(path)]
    if missing:
        raise FileNotFoundError(
            "Missing input file(s): " + ", ".join(missing) +
            ". Run the download step first (--download).")


def representative_domains_built(cursor):
    """True if RepresentativeDomains already exists and has been populated.

    Mirrors gffEnsemblBuilder's cached-.db-file check (os.path.exists(db_filename)):
    once built, a plain re-run should reuse the existing build instead of
    re-parsing everything from scratch.
    """
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='RepresentativeDomains';"
    )
    if cursor.fetchone() is None:
        return False
    cursor.execute("SELECT 1 FROM RepresentativeDomains LIMIT 1;")
    return cursor.fetchone() is not None


def clean_representative_domains(cursor):
    """Deletes the existing RepresentativeDomains build so it can be redone from scratch."""
    print("clean=True: dropping existing RepresentativeDomains table and protein_interpro_id mapping...")
    cursor.execute("DROP TABLE IF EXISTS RepresentativeDomains;")
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(Proteins);")}
    if "protein_interpro_id" in existing:
        cursor.execute("UPDATE Proteins SET protein_interpro_id = NULL WHERE protein_interpro_id IS NOT NULL;")
    if "protein_uniprot_isoform" in existing:
        cursor.execute("UPDATE Proteins SET protein_uniprot_isoform = NULL WHERE protein_uniprot_isoform IS NOT NULL;")
    if "interpro_domains_are_own" in existing:
        cursor.execute("UPDATE Proteins SET interpro_domains_are_own = NULL WHERE interpro_domains_are_own IS NOT NULL;")


def _split_ids(field):
    """idmapping's RefSeq and Ensembl columns hold "; "-separated lists. Reading
    such a field as one value is what UNIPROT_MAPPING_LOSES_CANONICALS.md
    describes; splitting is the whole point of this helper."""
    if not field:
        return ()
    return tuple(part.strip() for part in field.split(';') if part.strip())


def _claim(hits, pair, uniprot_acc, reviewed):
    """Record `uniprot_acc` for `pair`, preferring a reviewed entry.

    Values are (accession, reviewed). A reviewed entry displaces an unreviewed
    one; between two of equal status the first seen wins, so the result does not
    depend on where pandas happens to split its chunks.
    """
    previous = hits.get(pair)
    if previous is None or (reviewed and not previous[1]):
        hits[pair] = (uniprot_acc, reviewed)


def populate_dochap_protein_mapping(cursor, mapping_filepath,
                                    collision_strategy="ensembl", batch_size=500000):
    """
    Reads idmapping_selected.tab.gz via pandas and updates
    Proteins.protein_interpro_id.

    Column layout (0-indexed):
      0  = UniProt accession
      1  = UniProtKB-ID (mnemonic for reviewed entries, e.g. PTPRC_HUMAN;
           for unreviewed entries it is the accession itself, A0A2R8Y5B1_HUMAN)
      3  = RefSeq protein accessions (NP_.../XP_...)
      19 = Ensembl transcript IDs — col 18 is the gene ID (ENSG/ENSMUSG)

    Columns 3 and 19 are "; "-SEPARATED LISTS, not single values. One accession
    routinely names many transcripts: P08575 (CD45) lists 16 RefSeq proteins and
    9 Ensembl transcripts on one line. Reading either column as a single value
    silently drops every id but one - see
    DoChaP-db/UNIPROT_MAPPING_LOSES_CANONICALS.md. That defect left 31% of
    canonical transcripts with no accession, and therefore no domains at all,
    because populate_representative_domains() gates on membership of this column.

    Proteins stores versioned IDs (ENST00000641515.2) and idmapping may or may
    not carry the version, so each id is tried versioned first, then bare.

    Where two accessions name the same protein, a REVIEWED (Swiss-Prot) entry
    wins over an unreviewed (TrEMBL) one. Reviewed entries are identified from
    column 1: their mnemonic does not begin with the accession. This matters
    because TrEMBL entries are usually isoform-specific and so map 1:1, while
    the reviewed entry for a gene is exactly the one that lists many transcripts
    - so without this preference the fix above would hand canonical transcripts
    a fragment's accession instead of the gene's real one.
    """
    if collision_strategy not in COLLISION_STRATEGIES:
        raise ValueError(f"collision_strategy must be one of {COLLISION_STRATEGIES}")

    print("Step 1/2: Loading DoChaP protein IDs into memory...")
    rows = cursor.execute(
        "SELECT protein_refseq_id, protein_ensembl_id, transcript_ensembl_id FROM Proteins;"
    ).fetchall()

    refseq_to_pair            = {}
    transcript_ensembl_to_pair = {}

    for refseq_id, ensembl_id, transcript_ensembl_id in rows:
        pair = (refseq_id, ensembl_id)
        if refseq_id:
            refseq_to_pair[refseq_id] = pair
        if transcript_ensembl_id:
            transcript_ensembl_to_pair[transcript_ensembl_id] = pair
            enst_bare = transcript_ensembl_id.split('.')[0]
            if enst_bare != transcript_ensembl_id:
                transcript_ensembl_to_pair.setdefault(enst_bare, pair)

    print(f"   Loaded {len(rows):,} proteins "
          f"({len(refseq_to_pair):,} refseq, "
          f"{len(transcript_ensembl_to_pair):,} ensembl transcript IDs).")

    print("Step 1/2: Streaming UniProt ID mapping file (pandas)...")
    t0 = time.time()

    refseq_hits  = {}
    ensembl_hits = {}
    records_scanned = 0

    # pandas reads only the needed columns at C speed; chunksize keeps RAM flat
    reader = pd.read_csv(
        mapping_filepath,
        sep='\t',
        header=None,
        usecols=[0, 1, 3, 19],
        dtype=str,
        na_filter=False,   # keep empty strings as '', not NaN
        chunksize=1_000_000,
        compression='gzip',
        engine='c',
    )
    for chunk in reader:
        records_scanned += len(chunk)
        if records_scanned % 10_000_000 == 0:
            print(f"   Scanned {records_scanned:,} mapping lines "
                  f"({time.time()-t0:.0f}s)...")

        for uniprot_acc, uniprot_id, refseq_field, enst_field in chunk.itertuples(index=False, name=None):
            # A reviewed entry carries a mnemonic (PTPRC_HUMAN); an unreviewed
            # one repeats its accession (A0A2R8Y5B1_HUMAN).
            reviewed = bool(uniprot_id) and not uniprot_id.startswith(uniprot_acc)

            for refseq_id in _split_ids(refseq_field):
                pair = refseq_to_pair.get(refseq_id)
                if pair is not None:
                    _claim(refseq_hits, pair, uniprot_acc, reviewed)

            for enst_id in _split_ids(enst_field):
                # versioned first, then bare - a fallback for ONE id, which is
                # why it must not also terminate the loop over the list.
                pair = (transcript_ensembl_to_pair.get(enst_id)
                        or transcript_ensembl_to_pair.get(enst_id.split('.')[0]))
                if pair is not None:
                    _claim(ensembl_hits, pair, uniprot_acc, reviewed)

    print(f"   Scan complete in {time.time()-t0:.0f}s. "
          f"{len(refseq_hits):,} refseq hits, {len(ensembl_hits):,} ensembl hits.")

    # Resolve collisions
    all_pairs  = set(refseq_hits) | set(ensembl_hits)
    resolved   = {}
    collisions = 0

    reviewed_wins = 0
    for pair in all_pairs:
        r = refseq_hits.get(pair)
        e = ensembl_hits.get(pair)
        r_id, r_rev = r if r else (None, False)
        e_id, e_rev = e if e else (None, False)

        if r_id and e_id and r_id != e_id:
            # A reviewed entry settles it before the configured strategy does:
            # the two branches disagreeing usually means one of them found the
            # gene's Swiss-Prot entry and the other an isoform-specific TrEMBL
            # one, and the strategy has no way to tell those apart.
            if r_rev != e_rev:
                reviewed_wins += 1
                resolved[pair] = r_id if r_rev else e_id
                continue
            collisions += 1
            print(f"   WARNING: collision for protein "
                  f"(refseq={pair[0]}, ensembl={pair[1]}): "
                  f"refseq→{r_id} vs ensembl→{e_id}. "
                  f"Strategy: {collision_strategy}")
            if collision_strategy == "ignore":
                continue
            resolved[pair] = r_id if collision_strategy == "refseq" else e_id
        else:
            resolved[pair] = r_id or e_id

    if reviewed_wins:
        print(f"   {reviewed_wins:,} branch disagreements settled by preferring "
              f"the reviewed entry.")
    if collisions:
        print(f"   Total collisions: {collisions:,} (strategy='{collision_strategy}')."
              f" These are same-status disagreements only.")

    n_reviewed = sum(1 for v in resolved.values() if v)
    per_acc = collections.Counter(resolved.values())
    shared = sum(1 for n in per_acc.values() if n > 1)
    print(f"   {len(per_acc):,} distinct accessions over {n_reviewed:,} proteins; "
          f"{shared:,} accessions cover more than one transcript "
          f"(this was ~0 before the multi-value fix).")

    print(f"   Updating Proteins table with {len(resolved):,} interpro mappings...")
    update_query = """
        UPDATE Proteins SET protein_interpro_id = ?
        WHERE protein_refseq_id IS ? AND protein_ensembl_id IS ?;
    """
    batch = []
    for (refseq_id, ensembl_id), interpro_id in resolved.items():
        batch.append((interpro_id, refseq_id, ensembl_id))
        if len(batch) >= batch_size:
            cursor.executemany(update_query, batch)
            batch.clear()
    if batch:
        cursor.executemany(update_query, batch)

    print(f"   Proteins.protein_interpro_id populated for {len(resolved):,} proteins.")


def parse_interpro_entries(xml_filepath):
    """Stream interpro.xml.gz into {InterPro accession: (type, description)}.

    Each <interpro> entry carries its curated `type` attribute (Domain,
    Family, Homologous_superfamily, Repeat, Conserved_site, Active_site,
    Binding_site, PTM) and, in an <abstract> child, its description as mixed
    text and markup (<p>, <cite>, <db_xref>, ...). The type comes free from the
    same element we already visit for the description, so both are captured in
    one pass. We flatten the abstract with itertext() and collapse whitespace.
    An entry with no abstract still yields its type (description stays None).
    Both exist only for InterPro accessions, so member-database signatures that
    never got an <ipr> in the match file simply won't match.
    """
    print("Parsing InterPro entry types + descriptions from interpro.xml.gz...")
    t0 = time.time()

    entries = {}
    context = etree.iterparse(
        gzip.open(xml_filepath, 'rb'), events=('end',), tag='interpro'
    )
    for _, entry in context:
        ipr_id = entry.get('id')
        if ipr_id:
            etype = entry.get('type')
            abstract = entry.find('abstract')
            text = None
            if abstract is not None:
                flat = ' '.join(' '.join(abstract.itertext()).split())
                text = flat or None
            entries[ipr_id] = (etype, text)

        entry.clear()
        while entry.getprevious() is not None:
            del entry.getparent()[0]

    print(f"   Parsed {len(entries):,} InterPro entries "
          f"({time.time()-t0:.0f}s).")
    return entries


def populate_representative_domains(cursor, xml_filepath, entry_meta=None,
                                    batch_size=500000, use_threading=True):
    """
    Streams InterPro XML into RepresentativeDomains.

    By default uses a producer-consumer pattern: a parser thread (lxml C code,
    releases GIL) feeds a queue while the main thread writes batches to SQLite
    concurrently. Pass use_threading=False (or leave threads unavailable, e.g.
    on an HPC node that has hit its process/thread limit) to parse and insert
    in a single thread instead — slower, but works with zero extra threads.
    """
    print("Step 2/2: Loading known InterPro protein IDs from Proteins table...")
    known_interpro_ids = {
        row[0] for row in
        cursor.execute(
            "SELECT protein_interpro_id FROM Proteins WHERE protein_interpro_id IS NOT NULL;"
        )
    }
    print(f"   {len(known_interpro_ids):,} InterPro protein IDs to retain.")

    print("Step 2/2: Parsing InterPro match XML into RepresentativeDomains...")
    t0 = time.time()

    entry_meta = entry_meta or {}

    insert_query = """
        INSERT INTO RepresentativeDomains
               (protein_interpro_id, domain_id, domain_name, start, end, score, description, type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """

    def parse_batches():
        """Yield (batch, proteins_processed, proteins_inserted) as the XML is parsed."""
        batch = []
        proteins_processed = 0
        proteins_inserted  = 0

        context = etree.iterparse(
            gzip.open(xml_filepath, 'rb'), events=('end',), tag='protein'
        )
        for _, protein_elem in context:
            proteins_processed += 1
            prot_id = protein_elem.get('id')

            if prot_id in known_interpro_ids:
                proteins_inserted += 1
                for match_elem in protein_elem.findall('match'):
                    ipr_elem = match_elem.find('ipr')
                    ipr_id   = ipr_elem.get('id')   if ipr_elem is not None else match_elem.get('id')
                    ipr_name = ipr_elem.get('name') if ipr_elem is not None else match_elem.get('name')

                    for lcn_elem in match_elem.findall('lcn'):
                        if lcn_elem.get('representative') != 'true':
                            continue
                        start  = int(lcn_elem.get('start'))
                        end    = int(lcn_elem.get('end'))
                        score_s = lcn_elem.get('score')
                        score  = float(score_s) if score_s else None
                        etype, description = entry_meta.get(ipr_id, (None, None))
                        batch.append((prot_id, ipr_id, ipr_name, start, end, score, description, etype))

            protein_elem.clear()
            while protein_elem.getprevious() is not None:
                del protein_elem.getparent()[0]

            if len(batch) >= batch_size:
                yield batch, proteins_processed, proteins_inserted
                batch = []

        if batch:
            yield batch, proteins_processed, proteins_inserted

    total_rows     = 0
    last_processed = 0
    last_inserted  = 0

    def consume(batches_iter):
        nonlocal total_rows, last_processed, last_inserted
        for batch, proteins_processed, proteins_inserted in batches_iter:
            cursor.executemany(insert_query, batch)
            total_rows    += len(batch)
            last_processed = proteins_processed
            last_inserted  = proteins_inserted
            print(f"   Processed {proteins_processed:,} protein XML trees "
                  f"({proteins_inserted:,} inserted, {total_rows:,} rows, "
                  f"{time.time()-t0:.0f}s)...")

    thread = None
    if use_threading:
        work_queue = queue.Queue(maxsize=4)  # at most 4 batches buffered

        def producer():
            """Parse XML in a thread; lxml releases GIL during C-level work."""
            try:
                for item in parse_batches():
                    work_queue.put(item)
            finally:
                work_queue.put(None)  # sentinel, even on error

        try:
            thread = threading.Thread(target=producer, daemon=True)
            thread.start()
        except RuntimeError as e:
            print(f"   WARNING: couldn't start parser thread ({e}); "
                  f"falling back to single-threaded parsing.")
            thread = None

    if thread is not None:
        def queued_batches():
            while True:
                item = work_queue.get()
                if item is None:
                    return
                yield item

        consume(queued_batches())
        thread.join()
    else:
        consume(parse_batches())

    print(f"   RepresentativeDomains populated: {last_inserted:,} proteins, "
          f"{total_rows:,} total rows, {time.time()-t0:.0f}s.")


_BRACKET_RE = re.compile(r'\[([A-Za-z0-9]+-\d+)\]')
_DISPLAYED_RE = re.compile(r'IsoId=([^;]+);\s*Sequence=Displayed', re.IGNORECASE)
_ENSG_RE = re.compile(r'^ENS[A-Z]*G\d+')


def parse_uniprot_isoform_map(flatfile_path, keep_identifiers=None):
    """Stream uniprot_sprot.dat.gz into {identifier: (accession, isoform_id, is_own)}.

    `keep_identifiers`, when given, restricts what is retained to identifiers in
    that set. Swiss-Prot is ~576,000 entries covering every species, and holding
    every cross-reference it names costs over a gigabyte - nearly all of it ids
    this database has no protein for. Callers pass the ids they can actually use.

    `identifier` is any Ensembl or RefSeq transcript/protein id the entry
    cross-references, stored both versioned and bare because Proteins carries
    versioned ids and the flat file may or may not.

    `is_own` answers: does this accession's InterPro annotation describe the
    sequence THIS identifier encodes?

      1     yes - either the entry has no ALTERNATIVE PRODUCTS at all (one
            sequence, so every cross-reference points at it), or the
            cross-reference is tagged with the displayed isoform.
      0     no  - the cross-reference is tagged with a NON-displayed isoform.
            InterPro's match_complete.xml is keyed on canonical UniProtKB
            accessions only (it holds no '-n' isoform entries at all), so the
            rows filed under this accession describe a different sequence.
      None  unknown - an ALTERNATIVE PRODUCTS entry whose cross-reference
            carries no isoform tag. Left as NULL rather than guessed.

    Worked example, ARAP1 / Q96P48. The flat file says isoform 6 is Displayed
    and tags the seven Ensembl cross-references -6, -6, -6, -3, -1, -4, -7.
    Those tags partition the seven exactly by protein length (three at 1450 aa,
    then 1439, 1210, 1205, 1133), so the three -6 transcripts legitimately share
    the accession's domains - they are the same protein, differing only in UTR -
    and the other four do not.
    """
    print("Parsing UniProt isoform cross-references from uniprot_sprot.dat.gz...")
    t0 = time.time()

    isoform_map = {}
    entries = 0
    accession = None
    cc_lines = []
    dr_records = []

    def flush():
        """Resolve one finished entry into isoform_map."""
        if accession is None:
            return
        cc_text = ' '.join(cc_lines)
        has_alternatives = 'ALTERNATIVE PRODUCTS' in cc_text
        displayed = set()
        if has_alternatives:
            for match in _DISPLAYED_RE.finditer(cc_text):
                for iso in match.group(1).split(','):
                    iso = iso.strip()
                    if iso:
                        displayed.add(iso)

        for identifiers, tag in dr_records:
            if not has_alternatives:
                is_own = 1
            elif tag is None:
                is_own = None
            else:
                is_own = 1 if tag in displayed else 0
            for identifier in identifiers:
                if keep_identifiers is not None and identifier not in keep_identifiers:
                    continue
                previous = isoform_map.get(identifier)
                # A later entry only displaces an earlier one when it actually
                # knows something the earlier did not.
                if previous is None or (previous[2] is None and is_own is not None):
                    isoform_map[identifier] = (accession, tag, is_own)

    with gzip.open(flatfile_path, 'rt', encoding='utf-8', errors='replace') as handle:
        for line in handle:
            if line.startswith('AC   '):
                if accession is None:
                    first = line[5:].split(';')[0].strip()
                    if first:
                        accession = sys.intern(first)
            elif line.startswith('CC '):
                cc_lines.append(line[5:].strip())
            elif line.startswith('DR   Ensembl;') or line.startswith('DR   RefSeq;'):
                database, _, rest = line[5:].partition(';')
                match = _BRACKET_RE.search(rest)
                tag = match.group(1) if match else None
                if match:
                    rest = rest[:match.start()]
                identifiers = []
                for part in rest.split(';'):
                    part = part.strip().rstrip('.')
                    if not part or _ENSG_RE.match(part):
                        continue  # the gene id identifies no protein
                    identifiers.append(part)
                    bare = part.split('.')[0]
                    if bare != part:
                        identifiers.append(bare)
                if identifiers:
                    dr_records.append((identifiers, tag))
            elif line.startswith('//'):
                flush()
                entries += 1
                if entries % 100000 == 0:
                    print(f"   {entries:,} entries, {len(isoform_map):,} identifiers "
                          f"({time.time()-t0:.0f}s)...")
                accession = None
                cc_lines = []
                dr_records = []
        flush()

    print(f"   Parsed {entries:,} Swiss-Prot entries -> {len(isoform_map):,} "
          f"identifiers ({time.time()-t0:.0f}s).")
    return isoform_map


def populate_isoform_flags(cursor, flatfile_path, batch_size=500000):
    """Record, per protein, whether its accession's domains are really its own.

    populate_dochap_protein_mapping() hands one accession to every transcript
    UniProt lists for it, and RepresentativeDomains is keyed on that accession
    alone - there is no transcript or protein column in it. So every isoform
    sharing an accession reads back one domain list, at one set of amino-acid
    coordinates. Where those isoforms are the same protein that is correct;
    where they are not, the shorter ones inherit coordinates that were never
    theirs (ARAP1's 1205 aa isoform reports a SAM domain at aa 3-70 it cannot
    have, and a domain at 1277-1432 that does not fit inside it).

    This does NOT clear protein_interpro_id for those isoforms. Doing so would
    trade a wrong-domains problem for a worse one: the analysis would then see
    "canonical has domains, alternative has none" and emit a flood of false
    domain-loss events. The accession stays; consumers gate on
    interpro_domains_are_own and reposition or withhold accordingly.
    """
    # The proteins come first: their identifiers are what the flat-file scan is
    # allowed to retain, which keeps the map to this database's size rather than
    # Swiss-Prot's.
    print("Loading DoChaP protein identifiers...")
    rows = cursor.execute(
        "SELECT rowid, protein_ensembl_id, transcript_ensembl_id, "
        "       protein_refseq_id, transcript_refseq_id, protein_interpro_id "
        "FROM Proteins WHERE protein_interpro_id IS NOT NULL;"
    ).fetchall()
    wanted = set()
    for _, ensp, enst, refseq_protein, refseq_transcript, _accession in rows:
        for identifier in (ensp, enst, refseq_protein, refseq_transcript):
            if identifier:
                wanted.add(identifier)
                wanted.add(identifier.split('.')[0])
    print(f"   {len(rows):,} proteins carry an accession "
          f"({len(wanted):,} distinct identifiers to look for).")

    isoform_map = parse_uniprot_isoform_map(flatfile_path, keep_identifiers=wanted)

    # Idempotent: a re-run must decide from this run's evidence alone, never
    # inherit a previous run's verdict for a row it no longer matches.
    cursor.execute("UPDATE Proteins SET protein_uniprot_isoform = NULL, "
                   "interpro_domains_are_own = NULL "
                   "WHERE protein_uniprot_isoform IS NOT NULL "
                   "   OR interpro_domains_are_own IS NOT NULL;")

    print("Matching DoChaP proteins against UniProt isoforms...")

    updates = []
    unmatched = 0
    for rowid, ensp, enst, refseq_protein, refseq_transcript, accession in rows:
        accession = str(accession).strip()
        hit = None
        # The protein's own id first: it names the sequence directly, where a
        # transcript id only names something that encodes it.
        for identifier in (ensp, enst, refseq_protein, refseq_transcript):
            if not identifier:
                continue
            for candidate in (identifier, identifier.split('.')[0]):
                entry = isoform_map.get(candidate)
                # Only this accession's own entry may speak for this protein;
                # an entry for a different accession describes other domains.
                if entry is not None and entry[0] == accession:
                    hit = entry
                    break
            if hit is not None:
                break
        if hit is None:
            unmatched += 1
            continue
        updates.append((hit[1], hit[2], rowid))

    print(f"   {len(updates):,} matched, {unmatched:,} not found in Swiss-Prot "
          f"(TrEMBL-only accessions land here).")

    # Order matters. The fallback below is a structural guess; Swiss-Prot's
    # verdict is evidence, so the verdict is applied SECOND and overwrites it -
    # including an explicit unknown (NULL), which must not be silently upgraded
    # to "own" just because no sibling happens to share the accession.
    #
    # An accession held by exactly one protein has no sibling to be confused
    # with, so the rows filed under it can only refer to that protein. This
    # covers the TrEMBL 1:1 majority Swiss-Prot never mentions.
    cursor.execute(
        "UPDATE Proteins SET interpro_domains_are_own = 1 "
        "WHERE interpro_domains_are_own IS NULL AND protein_interpro_id IS NOT NULL "
        "  AND protein_interpro_id IN ("
        "      SELECT protein_interpro_id FROM Proteins "
        "      WHERE protein_interpro_id IS NOT NULL "
        "      GROUP BY protein_interpro_id HAVING COUNT(*) = 1);"
    )

    update_query = ("UPDATE Proteins SET protein_uniprot_isoform = ?, "
                    "interpro_domains_are_own = ? WHERE rowid = ?;")
    for start in range(0, len(updates), batch_size):
        cursor.executemany(update_query, updates[start:start + batch_size])

    counts = dict(cursor.execute(
        "SELECT CASE WHEN interpro_domains_are_own IS NULL THEN 'unknown' "
        "            WHEN interpro_domains_are_own = 1 THEN 'own' ELSE 'inherited' END, "
        "       COUNT(*) FROM Proteins WHERE protein_interpro_id IS NOT NULL "
        "GROUP BY 1;").fetchall())
    total = sum(counts.values()) or 1
    print("   interpro_domains_are_own:")
    for label in ('own', 'inherited', 'unknown'):
        n = counts.get(label, 0)
        print(f"      {label:<10} {n:>9,}  ({n / total * 100:.1f}%)")
    print("   'inherited' proteins must NOT be drawn or compared with this "
          "accession's domain coordinates as stored.")


class RepresentativeDomainsBuilder(SourceBuilder):
    """
    Download InterPro/UniProt mapping data and build the RepresentativeDomains
    table (plus Proteins.protein_interpro_id) inside DB_merged.sqlite.

    Unlike the per-species builders this runs once, after every species has
    already been merged into DB_merged.sqlite, so - like OrthologsBuilder -
    it takes no `species` argument. Download and build are separate steps
    (downloader()/parser()) so it plugs into the same Director flow as
    gffEnsemblBuilder etc., and can still be run standalone (see __main__).
    """

    def __init__(self, db_name=DB_NAME, clean=False, collision_strategy="ensembl", use_threading=True,
                 isoforms_only=False):
        self.db_name = db_name
        self.clean = clean
        self.collision_strategy = collision_strategy
        self.use_threading = use_threading
        self.isoforms_only = isoforms_only

    def downloader(self):
        if self.isoforms_only:
            download_file(UNIPROT_FTP_ADDRESS, UNIPROT_FLATFILE_FTP_PATH,
                          UNIPROT_LOCAL_PATH, UNIPROT_FLATFILE_NAME)
            return
        download_file(INTERPRO_FTP_ADDRESS, INTERPRO_FTP_PATH, INTERPRO_LOCAL_PATH, INTERPRO_FILE_NAME)
        download_file(INTERPRO_FTP_ADDRESS, INTERPRO_FTP_PATH, INTERPRO_LOCAL_PATH, INTERPRO_ENTRIES_FILE_NAME)
        download_file(UNIPROT_FTP_ADDRESS,  UNIPROT_FTP_PATH,  UNIPROT_LOCAL_PATH,  UNIPROT_FILE_NAME)
        download_file(UNIPROT_FTP_ADDRESS,  UNIPROT_FLATFILE_FTP_PATH,
                      UNIPROT_LOCAL_PATH,  UNIPROT_FLATFILE_NAME)

    def parser(self):
        conn = sqlite3.connect(self.db_name, check_same_thread=False)
        cursor = conn.cursor()

        try:
            if self.isoforms_only:
                # Backfill the isoform columns onto a database whose
                # RepresentativeDomains build is already done. Nothing else is
                # re-read: no idmapping scan, no InterPro XML, no rebuild of a
                # multi-GB table to add two columns.
                if not representative_domains_built(cursor):
                    raise RuntimeError(
                        "--isoforms-only needs an existing RepresentativeDomains build, "
                        "and this database has none. Run the full build first.")
                require_input_files(UNIPROT_FLATFILE)
                create_representative_domains_table(cursor)  # adds the columns if absent
                conn.commit()
                populate_isoform_flags(cursor, UNIPROT_FLATFILE)
                conn.commit()
                return

            if self.clean:
                clean_representative_domains(cursor)
                conn.commit()
            elif representative_domains_built(cursor):
                if isoform_flags_built(cursor):
                    print("RepresentativeDomains is already built (pass clean=True / --clean to force a rebuild). Skipping.")
                    return
                # Built before the isoform step existed. Skipping outright would
                # leave every isoform verdict NULL on a database that looks
                # complete, and the consumers would go on reading one isoform's
                # coordinates for all of them. The rest of the build is reused;
                # only the missing step runs.
                print("RepresentativeDomains is built, but the UniProt isoform step has not run "
                      "against it. Running that step alone (pass --clean to rebuild everything).")
                require_input_files(UNIPROT_FLATFILE)
                create_representative_domains_table(cursor)
                conn.commit()
                populate_isoform_flags(cursor, UNIPROT_FLATFILE)
                conn.commit()
                return

            require_input_files(UNIPROT_FILE, INTERPRO_FILE, INTERPRO_ENTRIES_FILE,
                                UNIPROT_FLATFILE)

            create_representative_domains_table(cursor)
            conn.commit()

            populate_dochap_protein_mapping(cursor, UNIPROT_FILE,
                                            collision_strategy=self.collision_strategy)
            conn.commit()

            entry_meta = parse_interpro_entries(INTERPRO_ENTRIES_FILE)
            populate_representative_domains(cursor, INTERPRO_FILE,
                                            entry_meta=entry_meta,
                                            use_threading=self.use_threading)
            conn.commit()

            # Runs last: it needs protein_interpro_id already assigned, and it
            # only annotates what the two steps above produced.
            populate_isoform_flags(cursor, UNIPROT_FLATFILE)
            conn.commit()

            print("Optimizing database...")
            cursor.execute("PRAGMA optimize;")
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"Error during pipeline: {e}")
            raise
        finally:
            conn.close()
            print("Done.")


if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser(
        description="Download and/or build the InterPro RepresentativeDomains table in DB_merged.sqlite."
    )
    argparser.add_argument("--download", action="store_true", help="Run only the download step")
    argparser.add_argument("--build", action="store_true", help="Run only the build step")
    argparser.add_argument("--clean", action="store_true",
                            help="Build step: delete the existing RepresentativeDomains build if present, then rebuild from scratch")
    argparser.add_argument("--collision-strategy", choices=COLLISION_STRATEGIES, default="ensembl")
    argparser.add_argument("--db", default=DB_NAME,
                            help=f"Database to build into (default: {DB_NAME} in the working "
                                 f"directory). The served copy usually lives elsewhere, e.g. "
                                 f"../DoChaP-web/DB_merged.sqlite.")
    argparser.add_argument("--isoforms-only", action="store_true",
                            help="Only add/refresh Proteins.protein_uniprot_isoform and "
                                 ".interpro_domains_are_own on a database that already has a "
                                 "RepresentativeDomains build. With --download, fetches just "
                                 "uniprot_sprot.dat.gz. Leaves every existing row untouched.")
    args = argparser.parse_args()

    # Neither flag given -> run both steps (matches the previous default behavior).
    do_download = args.download or not (args.download or args.build)
    do_build = args.build or not (args.download or args.build)

    # Set DOCHAP_NO_THREADING=1 to force single-threaded XML parsing, e.g. on
    # an HPC node where thread creation is failing (RuntimeError: can't start
    # new thread / RLIMIT_NPROC).
    use_threading = os.environ.get("DOCHAP_NO_THREADING", "0") != "1"

    builder = RepresentativeDomainsBuilder(db_name=args.db, clean=args.clean,
                                           collision_strategy=args.collision_strategy,
                                           use_threading=use_threading,
                                           isoforms_only=args.isoforms_only)
    if do_download:
        builder.downloader()
    if do_build:
        builder.parser()
