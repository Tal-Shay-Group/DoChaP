import gzip
import sqlite3
from lxml import etree
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

UNIPROT_FILE  = f"{UNIPROT_LOCAL_PATH}/{UNIPROT_FILE_NAME}"
INTERPRO_FILE = f"{INTERPRO_LOCAL_PATH}/{INTERPRO_FILE_NAME}"

COLLISION_STRATEGIES = ("ensembl", "refseq", "ignore")


def download_file(ftp_address, ftp_path, local_dir, file_name):
    http = httpsDownload('', ftp_address, ftp_path, savePath=local_dir,
                         files2Download=[[file_name, file_name]])
    http.Download(extract=False)


def create_representative_domains_table(cursor):
    """Adds RepresentativeDomains table and protein_interpro_id column to the DoChaP DB."""
    print("Creating RepresentativeDomains table and extending Proteins table...")

    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute("PRAGMA journal_mode = MEMORY;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RepresentativeDomains (
            protein_id TEXT,
            domain_id TEXT,
            domain_name TEXT,
            start INTEGER,
            end INTEGER,
            score REAL,
            status TEXT
        );
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_rep_domains_prot ON RepresentativeDomains(protein_id);"
    )

    # Add column only if it doesn't already exist
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(Proteins);")}
    if "protein_interpro_id" not in existing:
        cursor.execute("ALTER TABLE Proteins ADD COLUMN protein_interpro_id TEXT;")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_proteins_interpro ON Proteins(protein_interpro_id);"
        )


def populate_dochap_protein_mapping(cursor, mapping_filepath,
                                    collision_strategy="ensembl", batch_size=100000):
    """
    Streams idmapping_selected.tab.gz and updates Proteins.protein_interpro_id.

    For each DoChaP protein, looks up its UniProt (InterPro) accession via
    both refseq_id and ensembl_id. Issues a warning when they disagree and
    resolves the conflict according to collision_strategy:
        "ensembl" – use the ensembl-derived mapping (default)
        "refseq"  – use the refseq-derived mapping
        "ignore"  – leave protein_interpro_id NULL for conflicting rows
    """
    if collision_strategy not in COLLISION_STRATEGIES:
        raise ValueError(f"collision_strategy must be one of {COLLISION_STRATEGIES}")

    print(f"Step 1/2: Loading DoChaP protein IDs into memory...")
    rows = cursor.execute(
        "SELECT protein_refseq_id, protein_ensembl_id FROM Proteins;"
    ).fetchall()

    # Map each ID to the canonical (refseq, ensembl) pair for later UPDATE
    refseq_to_pair = {}
    ensembl_to_pair = {}
    for refseq_id, ensembl_id in rows:
        if refseq_id:
            refseq_to_pair[refseq_id] = (refseq_id, ensembl_id)
        if ensembl_id:
            ensembl_to_pair[ensembl_id] = (refseq_id, ensembl_id)

    print(f"   Loaded {len(rows):,} proteins "
          f"({len(refseq_to_pair):,} refseq, {len(ensembl_to_pair):,} ensembl IDs).")

    print("Step 1/2: Streaming UniProt ID mapping file...")
    # pair -> interpro_id resolved via refseq
    refseq_hits  = {}  # (refseq_id, ensembl_id) -> interpro_id
    # pair -> interpro_id resolved via ensembl
    ensembl_hits = {}  # (refseq_id, ensembl_id) -> interpro_id

    records_scanned = 0
    with gzip.open(mapping_filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            records_scanned += 1
            if records_scanned % 5_000_000 == 0:
                print(f"   Scanned {records_scanned:,} mapping lines...")

            columns = line.rstrip('\n').split('\t')
            if len(columns) < 19:
                continue

            interpro_id = columns[0]          # UniProt accession = InterPro protein id
            refseq_id   = columns[3] or None  # NCBI RefSeq protein ID
            ensembl_id  = columns[18] or None # Ensembl protein ID

            if refseq_id and refseq_id in refseq_to_pair:
                pair = refseq_to_pair[refseq_id]
                refseq_hits[pair] = interpro_id

            if ensembl_id and ensembl_id in ensembl_to_pair:
                pair = ensembl_to_pair[ensembl_id]
                ensembl_hits[pair] = interpro_id

    print(f"   Scan complete. {len(refseq_hits):,} refseq hits, "
          f"{len(ensembl_hits):,} ensembl hits.")

    # Resolve final mapping, detect collisions
    all_pairs = set(refseq_hits) | set(ensembl_hits)
    resolved  = {}   # (refseq_id, ensembl_id) -> interpro_id
    collisions = 0

    for pair in all_pairs:
        r_id = refseq_hits.get(pair)
        e_id = ensembl_hits.get(pair)

        if r_id and e_id and r_id != e_id:
            collisions += 1
            print(f"   WARNING: collision for protein "
                  f"(refseq={pair[0]}, ensembl={pair[1]}): "
                  f"refseq→{r_id} vs ensembl→{e_id}. "
                  f"Strategy: {collision_strategy}")
            if collision_strategy == "ignore":
                continue
            elif collision_strategy == "refseq":
                resolved[pair] = r_id
            else:  # ensembl (default)
                resolved[pair] = e_id
        else:
            resolved[pair] = r_id or e_id

    if collisions:
        print(f"   Total collisions: {collisions:,} (strategy='{collision_strategy}').")

    # Batch UPDATE
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


def populate_representative_domains(cursor, xml_filepath, batch_size=100000):
    """
    Streams InterPro XML and inserts domain matches into RepresentativeDomains,
    restricted to proteins already present in the DoChaP Proteins table.
    """
    print("Step 2/2: Loading known InterPro protein IDs from Proteins table...")
    known_interpro_ids = {
        row[0] for row in
        cursor.execute("SELECT protein_interpro_id FROM Proteins WHERE protein_interpro_id IS NOT NULL;")
    }
    print(f"   {len(known_interpro_ids):,} InterPro protein IDs to retain.")

    print("Step 2/2: Parsing InterPro match XML into RepresentativeDomains...")
    insert_query = """
        INSERT INTO RepresentativeDomains (protein_id, domain_id, domain_name, start, end, score, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    batch = []
    proteins_processed = 0
    proteins_inserted = 0

    context = etree.iterparse(gzip.open(xml_filepath, 'rb'), events=('end',), tag='protein')

    for event, protein_elem in context:
        proteins_processed += 1
        prot_id = protein_elem.get('id')

        if prot_id in known_interpro_ids:
            proteins_inserted += 1
            for interpro_elem in protein_elem.findall('interpro'):
                ipr_id   = interpro_elem.get('id')
                ipr_name = interpro_elem.get('name')
                for match_elem in interpro_elem.findall('match'):
                    for loc_elem in match_elem.findall('location'):
                        start  = int(loc_elem.get('start'))
                        end    = int(loc_elem.get('end'))
                        score  = float(loc_elem.get('score')) if loc_elem.get('score') else None
                        status = loc_elem.get('status')
                        batch.append((prot_id, ipr_id, ipr_name, start, end, score, status))

        protein_elem.clear()
        while protein_elem.getprevious() is not None:
            del protein_elem.getparent()[0]

        if len(batch) >= batch_size:
            cursor.executemany(insert_query, batch)
            batch.clear()
            print(f"   Processed {proteins_processed:,} protein XML trees "
                  f"({proteins_inserted:,} inserted)...")

    if batch:
        cursor.executemany(insert_query, batch)

    print(f"   RepresentativeDomains populated: {proteins_inserted:,} proteins "
          f"out of {proteins_processed:,} in XML.")


def main(collision_strategy="ensembl"):
    # 1. Download datasets
    download_file(INTERPRO_FTP_ADDRESS, INTERPRO_FTP_PATH, INTERPRO_LOCAL_PATH, INTERPRO_FILE_NAME)
    download_file(UNIPROT_FTP_ADDRESS,  UNIPROT_FTP_PATH,  UNIPROT_LOCAL_PATH,  UNIPROT_FILE_NAME)

    # 2. Extend DB_merged with new table and column
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        create_representative_domains_table(cursor)
        conn.commit()

        populate_dochap_protein_mapping(cursor, UNIPROT_FILE,
                                        collision_strategy=collision_strategy)
        conn.commit()

        populate_representative_domains(cursor, INTERPRO_FILE)
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
    main(collision_strategy="ensembl")
