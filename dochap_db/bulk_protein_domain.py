"""
bulk_protein_domains.py
-----------------------
Mass domain annotation for all proteins in a human GFF.

Strategy
--------
1. Extract protein IDs from GFF (Ensembl ENSP or NCBI NP_/XP_)
2. Map IDs → UniProt in bulk (MyGene.info POST, 1 000 IDs / request)
3. Download InterPro protein2ipr.dat.gz once and parse locally
4. Store everything in SQLite for fast range queries

Install: pip install requests gffutils pandas
"""

import logging
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"]      = "1"
os.environ["MKL_NUM_THREADS"]      = "1"
# NOW safe to import numpy/pandas
import gzip
import sys
import time
import io
import re
import sqlite3
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

# ─── paths ────────────────────────────────────────────────────────────────────
#GFF_PATH          = Path("Homo_sapiens.GRCh38.111.gff3.gz")
#PROTEIN2IPR_PATH  = Path("protein2ipr.dat.gz")          # downloaded once
#DB_PATH           = Path("human_protein_domains.sqlite")

PROTEIN2IPR_URL   = (
    "https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/"
    "protein2ipr.dat.gz"
)

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 – Extract protein IDs from GFF
# ─────────────────────────────────────────────────────────────────────────────

NCBI_RE    = re.compile(r'\b([NXY]P_\d+(?:\.\d+)?)\b')
ENSEMBL_RE = re.compile(r'\b(ENSP\d+(?:\.\d+)?)\b')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

def extract_protein_ids_from_gff(gff_path: Path) -> set[str]:
    """
    Scan GFF (plain or .gz) for all protein accessions in attribute columns.
    Works for both NCBI and Ensembl GFF3 flavours.
    """
    start_time = time.time()
    ids: set[str] = set()
    opener = gzip.open if str(gff_path).endswith(".gz") else open

    with opener(gff_path, "rt", errors="replace") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 9:
                continue
            attrs = cols[8]
            for m in NCBI_RE.finditer(attrs):
                ids.add(m.group(1).split(".")[0])   # strip version
            for m in ENSEMBL_RE.finditer(attrs):
                ids.add(m.group(1).split(".")[0])   # strip version
            #if len(ids) >= 25000:
            #    break

    
    print(f"Extracted {len(ids):,} unique protein IDs from GFF.")
    print(f"Duration: {time.time() -start_time}")
    return ids


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 – Bulk ID mapping → UniProt  (MyGene.info POST, 1 000 ids / batch)
# ─────────────────────────────────────────────────────────────────────────────

MYGENE_POST = "https://mygene.info/v3/query"
BATCH_SIZE  = 1_000

def batch_map_to_uniprot(protein_ids: set[str]) -> dict[str, str]:

    ncbi_ids    = [pid for pid in protein_ids if NCBI_RE.match(pid)]
    ensembl_ids = [pid for pid in protein_ids if ENSEMBL_RE.match(pid)]

    #print("IDs to map: %d NCBI RefSeq, %d Ensembl",
    #         len(ncbi_ids), len(ensembl_ids))

    mapping: dict[str, str] = {}

    for id_list, scope in [
        (ncbi_ids,    "refseq.protein"),
        (ensembl_ids, "ensembl.protein"),
    ]:
        if not id_list:
            continue

        for i in range(0, len(id_list), BATCH_SIZE):
            chunk = id_list[i : i + BATCH_SIZE]
            try:
                r = requests.post(
                    MYGENE_POST,
                    json={
                        "q":       chunk,
                        "scopes":  scope,
                        "fields":  "uniprot",
                        "species": "human",
                    },
                    timeout=30,
                )
                r.raise_for_status()
            except requests.RequestException as e:
                print("Batch %d failed (%s): %s", i, scope, e)
                time.sleep(2)
                continue

            hits = r.json() if isinstance(r.json(), list) else r.json().get("hits", [])

            found    = 0
            notfound = 0
            for hit in hits:
                if hit.get("notfound"):
                    notfound += 1
                    continue
                uniprot = hit.get("uniprot", {})
                acc = uniprot.get("Swiss-Prot") or uniprot.get("TrEMBL")
                if acc:
                    mapping[hit["query"]] = acc if isinstance(acc, str) else acc[0]
                    found += 1

            #print("  scope=%-20s  batch=%6d  found=%d  notfound=%d",
            #         scope, i, found, notfound)
            time.sleep(0.2)

    #log.info("Total mapped: %d / %d", len(mapping), len(protein_ids))
    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 – Download protein2ipr.dat.gz (once)
# ─────────────────────────────────────────────────────────────────────────────

def ensure_protein2ipr(path: Path, url: str = PROTEIN2IPR_URL) -> None:
    if path.exists():
        print(f"protein2ipr.dat.gz already present ({path.stat().st_size/1e9:.1f} GB).")
        return
    start_time = time.time()
    print(f"Downloading protein2ipr.dat.gz (~3 GB) …")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total  = int(r.headers.get("content-length", 0))
        with open(path, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    print("Download complete.")
    print(f"Duration: {time.time() -start_time}")


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 – Parse protein2ipr.dat.gz for our UniProt accessions
# ─────────────────────────────────────────────────────────────────────────────

# protein2ipr columns (tab-separated, no header):
# 0: UniProt acc  1: InterPro acc  2: InterPro name  3: source DB name
# 4: source accession  5: pos_start  6: pos_end
# accession prefix → database name
ACC_PREFIX_TO_DB = {
    "PF":   "Pfam",
    "SM":   "SMART",
    "cd":   "CDD",
    "PS":   "PROSITE",
    "PR":   "PRINTS",
    "PIRSF":"PIRSF",
    "MF":   "HAMAP",
    "NCBIfam": "NCBIfam",
    "TIGR": "TIGRfam",
    "G3DSA":"Gene3D",
    "SSF":  "SUPERFAMILY",
}

def acc_to_db(acc: str) -> str:
    for prefix, db in ACC_PREFIX_TO_DB.items():
        if acc.startswith(prefix):
            return db
    return "unknown"


def parse_protein2ipr(path: Path, keep_uniprot: set[str]) -> pd.DataFrame:

    if not keep_uniprot:
        log.error("keep_uniprot is empty — aborting.")
        return pd.DataFrame(columns=[
            "uniprot_id", "interpro_acc", "interpro_name",
            "db", "db_accession", "aa_start", "aa_end",
        ])

    log.info("Filtering protein2ipr against %d UniProt accessions.", len(keep_uniprot))

    rows        = []
    line_count  = 0
    kept_count  = 0
    t_start     = time.monotonic()
    t_last      = t_start
    compressed_size = os.path.getsize(path)

    with gzip.open(path, "rt") as fh:
        raw = fh.buffer.fileobj

        for line in fh:
            line_count += 1
            parts = line.rstrip("\n").split("\t")

            # log first 3 lines so we can verify the format
            if line_count <= 3:
                log.info("Sample line %d (%d cols): %s", line_count, len(parts), parts)

            if len(parts) < 6:          # was 7 — file has 6 columns
                continue

            uniprot = parts[0]
            if uniprot not in keep_uniprot:
                continue

            try:
                db_acc = parts[3]
                rows.append({
                    "uniprot_id":   uniprot,
                    "interpro_acc": parts[1],
                    "interpro_name":parts[2],
                    "db_accession": db_acc,
                    "db":           acc_to_db(db_acc),   # derived from prefix
                    "aa_start":     int(parts[4]),
                    "aa_end":       int(parts[5]),
                })
                kept_count += 1
            except (ValueError, IndexError) as e:
                log.warning("Malformed line %d: %s — %s", line_count, parts, e)
                continue

            now = time.monotonic()
            if line_count % 1_000_000 == 0 or (now - t_last) >= 60:
                pct     = raw.tell() / compressed_size * 100
                elapsed = now - t_start
                eta     = (elapsed / pct * (100 - pct)) if pct > 0 else 0
                log.info("  %5.1f%%  lines=%10d  kept=%8d  ETA=%ds",
                         pct, line_count, kept_count, int(eta))
                t_last = now

    elapsed = time.monotonic() - t_start
    log.info("Done. lines=%d  kept=%d  elapsed=%.1fs", line_count, kept_count, elapsed)

    if not rows:
        log.error("No rows kept. Sample keep_uniprot: %s", list(keep_uniprot)[:5])
        return pd.DataFrame(columns=[
            "uniprot_id", "interpro_acc", "interpro_name",
            "db", "db_accession", "aa_start", "aa_end",
        ])

    df = pd.DataFrame(rows)
    log.info("Kept %d annotations for %d proteins.", len(df), df["uniprot_id"].nunique())
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 – Store in SQLite with indexes for fast range queries
# ─────────────────────────────────────────────────────────────────────────────

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS id_map (
    protein_id  TEXT PRIMARY KEY,
    uniprot_id  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS domains (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    uniprot_id    TEXT    NOT NULL,
    interpro_acc  TEXT,
    interpro_name TEXT,
    db            TEXT,
    db_accession  TEXT,
    aa_start      INTEGER NOT NULL,
    aa_end        INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_domains_uniprot  ON domains(uniprot_id);
CREATE INDEX IF NOT EXISTS idx_domains_range    ON domains(uniprot_id, aa_start, aa_end);
CREATE INDEX IF NOT EXISTS idx_idmap_uniprot    ON id_map(uniprot_id);
"""


def store_to_sqlite(
    db_path:  Path,
    id_map:   dict[str, str],
    domains:  pd.DataFrame,
) -> None:
    start_time = time.time()
    con = sqlite3.connect(db_path)
    con.executescript(CREATE_SQL)

    # id_map table
    con.executemany(
        "INSERT OR REPLACE INTO id_map VALUES (?, ?)",
        id_map.items(),
    )

    # domains table
    domains.to_sql("domains", con, if_exists="append", index=False,
                   chunksize=50_000)
    con.commit()
    con.close()
    print(f"Saved to {db_path}.")
    print(f"Duration: {time.time() -start_time}")
 

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 – Query helper  (the fast runtime interface after DB is built)
# ─────────────────────────────────────────────────────────────────────────────

def query_domains(
    db_path:    Path,
    protein_id: str,
    aa_start:   Optional[int] = None,
    aa_end:     Optional[int] = None,
) -> pd.DataFrame:
    """
    Look up domains for a protein ID (NCBI or Ensembl) with optional
    amino-acid range filter.  Sub-millisecond after DB is built.
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    # Resolve protein_id → uniprot_id
    row = con.execute(
        "SELECT uniprot_id FROM id_map WHERE protein_id = ?",
        (protein_id.split(".")[0],)
    ).fetchone()
    if row is None:
        print(f"No UniProt mapping found for {protein_id!r}.")
        return pd.DataFrame()

    uniprot_id = row["uniprot_id"]

    if aa_start is not None and aa_end is not None:
        sql = """
            SELECT * FROM domains
            WHERE uniprot_id = ?
              AND aa_start <= ?
              AND aa_end   >= ?
            ORDER BY aa_start
        """
        df = pd.read_sql_query(sql, con, params=(uniprot_id, aa_end, aa_start))
    else:
        df = pd.read_sql_query(
            "SELECT * FROM domains WHERE uniprot_id = ? ORDER BY aa_start",
            con, params=(uniprot_id,)
        )

    con.close()
    return df


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    GFF_PATH = Path(sys.argv[1])
    PROTEIN2IPR_PATH = Path(sys.argv[2])
    DB_PATH = Path(sys.argv[3])
    # ── Build the database (run once) ────────────────────────────────────────
    if not DB_PATH.exists():
        print("=== Building domain database ===")

        protein_ids = extract_protein_ids_from_gff(GFF_PATH)
        id_map      = batch_map_to_uniprot(protein_ids)
        uniprot_ids = set(id_map.values())

        ensure_protein2ipr(PROTEIN2IPR_PATH)
        domains = parse_protein2ipr(PROTEIN2IPR_PATH, uniprot_ids)

        store_to_sqlite(DB_PATH, id_map, domains)
        print("=== Database ready ===\n")

    # ── Query (milliseconds) ──────────────────────────────────────────────────
    #result = query_domains(DB_PATH, "NP_000537.3", aa_start=100, aa_end=290)
    result = query_domains(DB_PATH, "NP_001087.2", aa_start=1, aa_end=419)
    result = query_domains(DB_PATH, "NP_001290203.1", aa_start=1, aa_end=1500)
    print(result[["db", "db_accession", "interpro_name", "aa_start", "aa_end"]])
