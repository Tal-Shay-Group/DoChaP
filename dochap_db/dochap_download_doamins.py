"""
Build a flat file:  NCBI/Ensembl protein ID  →  domains
by joining idmapping.dat.gz + protein2ipr.dat.gz locally.
No API calls needed after download.
"""

import gzip
import os
import sqlite3
import time
import logging
from pathlib import Path
import pandas as pd

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── FTP URLs ──────────────────────────────────────────────────────────────────
IDMAP_URL = (
    "https://ftp.uniprot.org/pub/databases/uniprot/current_release/"
    "knowledgebase/idmapping/by_organism/HUMAN_9606_idmapping.dat.gz"
)
PROTEIN2IPR_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/"
    "protein2ipr.dat.gz"
)

# ID types in idmapping.dat.gz we care about
'''
['Allergome', 'BioCyc', 'BioGRID', 'BioMuta', 'CCDS', 'CPTAC',
'CRC64', 'ChEMBL', 'ChiTaRS', 'ComplexPortal', 'DIP', 'DMDM',
'DNASU', 'DisProt', 'DrugBank', 'EMBL', 'EMBL-CDS', 'EMDB',
'ESTHER', 'Ensembl', 'Ensembl_PRO', 'Ensembl_TRS', 'GI',
'GeneCards', 'GeneID', 'GeneReviews', 'GeneTree', 'GeneWiki',
'Gene_Name', 'Gene_ORFName', 'Gene_Synonym', 'GenomeRNAi',
'GlyConnect', 'GuidetoPHARMACOLOGY', 'HGNC', 'HOGENOM', 'IDEAL',
'KEGG', 'MEROPS', 'MIM', 'MINT', 'NCBI_TaxID', 'OMA',
'OpenTargets', 'Orphanet', 'OrthoDB', 'PATRIC', 'PDB',
'PeroxiBase', 'ProteomicsDB', 'REBASE', 'Reactome', 'RefSeq',
'RefSeq_NT', 'STRING', 'SwissLipids', 'TCDB', 'UCSC', 'UniParc',
'UniPathway', 'UniProtKB-ID', 'UniRef100', 'UniRef50', 'UniRef90',
'VEuPathDB', 'eggNOG']
'''
WANTED_ID_TYPES = {"RefSeq", "Ensembl_PRO", "CCDS", "HGNC"}


# ── Download helper ───────────────────────────────────────────────────────────

def download(url: str, path: Path) -> None:
    if path.exists():
        log.info("%s already present (%.1f GB).",
                 path.name, path.stat().st_size / 1e9)
        return
    log.info("Downloading %s ...", url)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done  = 0
        with open(path, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
                done += len(chunk)
                if total:
                    log.info("  %.1f%%", done / total * 100)
    log.info("Done: %s", path)


# ── Step 1: parse idmapping → {external_id: uniprot_acc} ─────────────────────

def parse_idmapping(path: Path) -> dict[str, str]:
    """
    Returns mapping:  RefSeq/Ensembl protein ID  →  UniProt accession
    Keeps only human RefSeq_Protein and Ensembl_PRO entries.
    """
    id_mapping: dict[str, str] = {} # ext_id -> (ext_db, uniprot)
    db_mapping: dict[str, int] = {} # ext_id -> source
    db_map: dict[str, int] = {} # avoid repeating db name refseq->0, ensembl-> 1, etc
    line_count = 0
    t_start = t_last = time.monotonic()
    compressed_size = os.path.getsize(path)

    log.info("Parsing idmapping file ...")

    for idx, db in enumerate(WANTED_ID_TYPES):
        db_map[db] = idx

    with gzip.open(path, "rt") as fh:
        raw = fh.buffer.fileobj
        for line in fh:
            line_count += 1
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue

            uniprot, id_type, ext_id = parts
            if id_type not in WANTED_ID_TYPES:
                continue

            # strip version suffix for RefSeq (NP_001087.2 → NP_001087)
            #key = ext_id.split(".")[0] if id_type == "RefSeq" else ext_id
            id_mapping[ext_id] = uniprot
            db_mapping[ext_id] = db_map[id_type]

            now = time.monotonic()
            if line_count % 1_000_000 == 0 or (now - t_last) >= 60:
                pct = raw.tell() / compressed_size * 100
                eta = ((now - t_start) / pct * (100 - pct)) if pct else 0
                log.info("  %5.1f%%  lines=%d  mapped=%d  ETA=%ds",
                         pct, line_count, len(mapping), int(eta))
                t_last = now

    log.info("idmapping done. %d external IDs → UniProt.", len(id_mapping))
    return db_map, db_mapping, id_mapping


# ── Step 2: parse protein2ipr, keeping only our UniProt accessions ────────────

ACC_PREFIX_TO_DB = {
    "PF":    "Pfam",       "SM":   "SMART",     "cd":    "CDD",
    "PS":    "PROSITE",    "PR":   "PRINTS",     "PIRSF":"PIRSF",
    "MF":    "HAMAP",      "TIGR": "TIGRfam",   "NF":   "NCBIfam",
    "PLN":   "NCBI_Plant", "PRK":  "NCBI_Prok", "G3DSA":"Gene3D",
    "SSF":   "SUPERFAMILY","PTHR": "PANTHER",
}

def acc_to_db(acc: str) -> str:
    for prefix, db in ACC_PREFIX_TO_DB.items():
        if acc.startswith(prefix):
            return db
    return "other"


def parse_protein2ipr(
    path: Path,
    keep_uniprot: set[str],
) -> list[dict]:
    rows = []
    line_count = kept_count = 0
    t_start = t_last = time.monotonic()
    compressed_size = os.path.getsize(path)

    log.info("Parsing protein2ipr against %d UniProt IDs ...", len(keep_uniprot))

    with gzip.open(path, "rt") as fh:
        raw = fh.buffer.fileobj
        for line in fh:
            line_count += 1
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            if line_count <= 3:
                log.info("Sample line %d: %s", line_count, parts)

            uniprot = parts[0]
            if uniprot not in keep_uniprot:
                continue

            db_acc = parts[3]
            try:
                rows.append({
                    "uniprot_id":    uniprot,
                    "interpro_acc":  parts[1],
                    "interpro_name": parts[2],
                    "db":            acc_to_db(db_acc),
                    "db_accession":  db_acc,
                    "aa_start":      int(parts[4]),
                    "aa_end":        int(parts[5]),
                })
                kept_count += 1
            except (ValueError, IndexError):
                continue

            now = time.monotonic()
            if line_count % 1_000_000 == 0 or (now - t_last) >= 60:
                pct = raw.tell() / compressed_size * 100
                eta = ((now - t_start) / pct * (100 - pct)) if pct else 0
                log.info("  %5.1f%%  lines=%d  kept=%d  ETA=%ds",
                         pct, line_count, kept_count, int(eta))
                t_last = now
                

    log.info("protein2ipr done. kept=%d annotations.", len(rows))
    return rows


# ── Step 3: store everything in SQLite ────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_mapping (
    ext_id      TEXT PRIMARY KEY,   -- RefSeq | Ensembl_PRO | CCDS | HGNS
    source_type     INT NOT NULL    -- key
);

CREATE TABLE IF NOT EXISTS ext_to_uniprot (
    ext_id      TEXT PRIMARY KEY,   -- NP_001087.1 or ENSP00000253792.1
    source_type INT  NOT NULL,      -- The key from source mapping
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

CREATE INDEX IF NOT EXISTS idx_ext       ON ext_to_uniprot(ext_id);
CREATE INDEX IF NOT EXISTS idx_uniprot   ON ext_to_uniprot(uniprot_id);
CREATE INDEX IF NOT EXISTS idx_dom_uni   ON domains(uniprot_id);
CREATE INDEX IF NOT EXISTS idx_dom_range ON domains(uniprot_id, aa_start, aa_end);
"""


def build_db(
    db_path:    Path,
    idmap_path: Path,
    ipr_path:   Path,
) -> None:
    # 1. parse idmapping
    db_map, db_mapping, ext_to_uniprot = parse_idmapping(idmap_path)
    keep_uniprot   = set(ext_to_uniprot.values())

    # 2. parse protein2ipr
    domain_rows = parse_protein2ipr(ipr_path, keep_uniprot)

    # 3. write SQLite
    log.info("Writing SQLite database ...")
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)

    con.executemany(
        "INSERT OR REPLACE INTO source_mapping VALUES (?,?)",
        (
            (key,
             value)
            for key, value in db_map.items()
        ),
    )

    con.executemany(
        "INSERT OR REPLACE INTO ext_to_uniprot VALUES (?,?,?)",
        (
            (ext_id,
             db_mapping[ext_id],
             uniprot)   
            for ext_id, uniprot in ext_to_uniprot.items()
        ),
    )

    con.executemany(
        """INSERT INTO domains
           (uniprot_id,interpro_acc,interpro_name,db,db_accession,aa_start,aa_end)
           VALUES (:uniprot_id,:interpro_acc,:interpro_name,
                   :db,:db_accession,:aa_start,:aa_end)""",
        domain_rows,
    )
    con.commit()
    con.close()
    log.info("Database ready: %s", db_path)


# ── Query interface ───────────────────────────────────────────────────────────

def query_domains(
    con:    sqlite3.Connection,
    protein_id: str,            # NP_001087.2  or  ENSP00000253792
    aa_start:   int = None,
    aa_end:     int = None,
):
    #key = protein_id.split(".")[0]   # strip version
    key = protein_id

    row = con.execute(
        "SELECT uniprot_id FROM ext_to_uniprot WHERE ext_id = ?", (key,)
    ).fetchone()

    if row is None:
        log.warning("No UniProt mapping for %s", protein_id)
        return []

    uniprot_id = row[0].split('-')[0] # remove -version like P53396-1

    if aa_start and aa_end:
        sql = """
            SELECT db, db_accession, interpro_acc, interpro_name,
                   aa_start, aa_end
            FROM domains
            WHERE uniprot_id = ?
              AND aa_start  <= ?
              AND aa_end    >= ?
            ORDER BY aa_start
        """
        rows = con.execute(sql, (uniprot_id, aa_end, aa_start)).fetchall()
    else:
        rows = con.execute(
            """SELECT db, db_accession, interpro_acc, interpro_name,
                      aa_start, aa_end
               FROM domains WHERE uniprot_id = ? ORDER BY aa_start""",
            (uniprot_id,)
        ).fetchall()

    return rows

def create_domain_types(con: sqlite3.Connection):
    # create domain types table and populate it with unique interpro_acc entries
    columns = ['type_id', 'name', 'other_name', 'description', 'CDD_id', 'cdd', 'pfam', 'smart', 'tigr', 'interpro']
    rows = []
    df_interpro_domain_type_id = {}
    df_domains = pd.read_sql_query("SELECT * FROM domains", con)
    groups =  df_domains.groupby("interpro_acc").groups
    counter = 0
    for interpro_acc, indices in groups.items():
        name, other_name, description = None, None, None
        cdd, pfam, smart, tigr, interpro = None, None, None, None, None
        counter += 1
        accessions = set(df_domains.loc[indices, 'db_accession']) 
        names = set(df_domains.loc[indices, 'interpro_name'])
        
        cur_df = df_domains.loc[indices]
        pfam = ";".join(set(cur_df.loc[cur_df['db'].str.lower() == 'pfam', 'db_accession']))
        smart = ";".join(set(cur_df.loc[cur_df['db'].str.lower() == 'smart', 'db_accession']))
        tigr = ";".join(set(cur_df.loc[cur_df['db'].str.lower() == 'tigrfam', 'db_accession']))
        cdd = ";".join(set(cur_df.loc[cur_df['db'].str.lower() == 'cdd', 'db_accession']))
        name = next(iter(names))
        other_name = ";".join(names)
        rows.append((counter, name, other_name, description, None, cdd, pfam, smart, tigr, interpro_acc)) 
        df_interpro_domain_type_id[interpro_acc] = counter
    df_domain_types = pd.DataFrame(rows, columns=columns)
    return df_domain_types, df_interpro_domain_type_id
    
# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    IDMAP_PATH = Path("HUMAN_9606_idmapping.dat.gz")
    IPR_PATH   = Path("protein2ipr.dat.gz")
    DB_PATH    = Path("protein_domains.sqlite")

    download(IDMAP_URL,       IDMAP_PATH)
    download(PROTEIN2IPR_URL, IPR_PATH)

    if not DB_PATH.exists():
        build_db(DB_PATH, IDMAP_PATH, IPR_PATH)

    # example queries
    con = sqlite3.connect(DB_PATH)
    create_domain_types(con)
    for pid in ["NP_001087.2", "NP_942127.1", "ENSP00000253792.2", "NP_001014840.1"]:
        hits = query_domains(con, pid, aa_start=1, aa_end=2000)
        print(f"\n{pid}  →  {len(hits)} domain hits")
        for h in hits:
            print(f"  {h[0]:<14} {h[1]:<14} {h[3]:<45} {h[4]:>5}-{h[5]}")
    con.close()