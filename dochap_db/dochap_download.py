import os
from pathlib import Path
import requests
import re
import gzip
import shutil
import time
import sys
import argparse
from ftplib import FTP
import pandas as pd
from io import StringIO
import mysql.connector

ROOT_DIR = Path("./genomic_data")
BIOMART_URL = "http://www.ensembl.org/biomart/martservice"
MAX_RETRIES = 5
SpeciesConvention = {
    'M_musculus': {'name': 'Mus_musculus', 'ncbi_tagid': '10090'},
    'H_sapiens': {'name': 'Homo_sapiens', 'ncbi_tagid': '9606'},
    'R_norvegicus': {'name': 'Rattus_norvegicus', 'ncbi_tagid': '10116'},
    'D_rerio': {'name': 'Danio_rerio', 'ncbi_tagid': '7955'}, 
    'X_tropicalis': {'name': 'Xenopus_tropicalis', 'ncbi_tagid': '8364'},
}

ENSEMBL_SPECIES_INFO = {
    "H_sapiens": {"name": "homo_sapiens"},
    "M_musculus": {"name": "mus_musculus"},
    "R_norvegicus": {"name": "rattus_norvegicus"},
    "D_rerio": {"name": "danio_rerio"},
    "X_tropicalis": {"name": "xenopus_tropicalis"}
}

# Species shortcuts mapping
SPECIES_SHORTCUTS = {
    'H': 'H_sapiens',
    'M': 'M_musculus',
    'R': 'R_norvegicus',
    'D': 'D_rerio',
    'X': 'X_tropicalis'
}

def get_ncbi_latest_release_by_tag(tagid):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    # URL 1: ESearch - Find the latest RefSeq UID for the TaxID
    search_params = {
        "db": "assembly",
        "term": f"txid{tagid}[Organism] AND latest_refseq[Property]",
        "retmode": "json"
    }
    
    try:
        search_res = requests.get(base_url + "esearch.fcgi", params=search_params)
        search_res.raise_for_status()
        id_list = search_res.json().get('esearchresult', {}).get('idlist', [])
        
        if not id_list:
            return f"No GCF release found for TaxID {tagid}."
        
        # The first ID in the list is the most recent
        uid = id_list[0]
        
        # URL 2: ESummary - Get the metadata for that UID
        summary_params = {
            "db": "assembly",
            "id": uid,
            "retmode": "json"
        }
        
        summary_res = requests.get(base_url + "esummary.fcgi", params=summary_params)
        summary_res.raise_for_status()
        
        # Extract the assemblyaccession (the GCF string)
        summary_data = summary_res.json()
        release_string = summary_data['result'][uid]['assemblyaccession']
        return release_string

    except Exception as e:
        return f"Error: {e}"

def download_ncbi(specie, release='latest', output_dir="."):
    """ Downloads GFF3 GPFF from NCBI RefSeq based on the latest assembly for the given specie.  """
    print(f"\n[NCBI] Downloading {specie} (Release: {release}). Writing to: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    # Clean the specie name for NCBI (e.g., Xenopus_tropicalis -> "Xenopus tropicalis")
    specie_clean = specie.replace("_", " ")
    txid = SpeciesConvention[specie]['ncbi_tagid']
    
    accession = get_ncbi_latest_release_by_tag(txid) if release == 'latest' else release
    print(f"\trelease: {accession}")
    acc_num = accession.split('_')[1].split('.')[0]
    f1, f2, f3 = acc_num[0:3], acc_num[3:6], acc_num[6:9]  # GCF_000004195.4 -> parts: ['000', '000', '419', '5'] (example logic)
    
    base_url = f"https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/{f1}/{f2}/{f3}/"
    
    try:
        # Find the full folder name (it includes the assembly name)
        dir_listing = requests.get(base_url, timeout=30).text
        # Look for the folder starting with our accession
        folder_match = re.search(fr'({accession}[^/"]+)/', dir_listing)
        if not folder_match:
            raise Exception(f"Could not find folder for {accession} at {base_url}")
        
        full_folder = folder_match.group(1)
        # Download GFF and protein GPFF files
        files_to_download = {
            "gff": f"{full_folder}_genomic.gff.gz",
            "gpff": f"{full_folder}_protein.gpff.gz"
        }        
        downloaded_paths = {}
        for file_type, file_name in files_to_download.items():
            file_url = f"{base_url}{full_folder}/{file_name}"
            dest_path = os.path.join(output_dir, file_name)      
            print(f"\tDownloading {file_type}: {file_url}")
            try:
                with requests.get(file_url, stream=True, timeout=120) as r:
                    r.raise_for_status()
                    with open(dest_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            f.write(chunk)
                print(f"\tDone {file_type}: {dest_path}")
                downloaded_paths[file_type] = dest_path
            except Exception as e:
                print(f"\tWarning: Could not download {file_type}: {e}")       
        print(f"\tNCBI Match: {accession}")
        return downloaded_paths
    except Exception as e:
        print(f"Download error: {e}")
        return None

def get_ensembl_latest_release():
    try:
        r_info = requests.get("https://rest.ensembl.org/info/software?content-type=application/json", timeout=30)
        r_info.raise_for_status()
        release_num = r_info.json()['release']
    except:
        print("Error: Could not retrieve latest Ensembl release. Defaulting to 110.")
        raise
    return release_num

def download_ensembl_gff(specie, release='latest', output_dir="."):
    """ Downloads GFF3 from Ensembl. """
    print(f"\n[Ensembl] Downloading {specie} (Release: {release}). Writing to: {output_dir}")
    if specie not in ENSEMBL_SPECIES_INFO:
        print(f"  Error: Species {specie} not configured for Ensembl download")
        return None
    
    release_num = get_ensembl_latest_release() if release == 'latest' else release
    specie_info = ENSEMBL_SPECIES_INFO[specie]
    specie_name = specie_info["name"]
    
    local_dir = Path(ROOT_DIR) / specie / "ensembl"
    local_dir.mkdir(parents=True, exist_ok=True)
    # Folder names in the URL path are ALWAYS lowercase
    specie_folder = specie_name.lower()
    
    # Define the directory URL
    base_ftp = f"https://ftp.ensembl.org/pub/release-{release_num}/gff3/{specie_folder}/"
    
    print(f"\tConnecting to Ensembl directory: {base_ftp}")
    try:
        # Request the directory listing (the HTML page showing the list of files)
        response = requests.get(base_ftp, timeout=60)
        response.raise_for_status()
        
        # SCRAPE the actual filenames from the HTML
        # This grabs the exact casing used on the server (e.g., lowercase 't' in tropicalis)
        links = re.findall(r'href="([^"]+\.gff3\.gz)"', response.text)
        
        # Filter for the "Primary" genomic file
        # We exclude 'chr' (individual chromosomes), 'abinitio', and 'semimanaged'
        target_file = None
        for link in links:
            # Must contain the release number and NOT contain specific keywords
            if str(release_num) in link:
                if not any(x in link.lower() for x in ['chr.', 'abinitio', 'semimanaged', 'chr_patch', 'chromosome']):
                    target_file = link
                    break
        
        if not target_file:
            raise FileNotFoundError(f"Could not find a primary GFF3 file in {base_ftp}")

        # 6. Build the final URL using the EXACT string found on the server
        file_url = base_ftp + target_file
        dest_path = os.path.join(output_dir, target_file)

        print(f"\tVerified filename found: {target_file}")
        print(f"\tDownloading from: {file_url}")
        
        with requests.get(file_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                    
        print(f"\tSuccessfully downloaded: {dest_path}")
        return dest_path

    except requests.exceptions.HTTPError as e:
        print(f"\tHTTP Error: {e}. Check if specie {specie_folder}' exists in release {release_num}.")
    except Exception as e:
        print(f"\tAn unexpected error occurred: {e}")
        return None

def run_biomart_query(xml, out_file):
    for i in range(MAX_RETRIES): # Retry logic
        try:
            r = requests.get(BIOMART_URL, params={'query': xml}, timeout=300)
            if r.status_code == 200:
                with open(out_file, "w") as f:
                    f.write(r.text)
                return True
        except Exception as e:
            print(f"  Attempt {i+1} failed: {e}")
            time.sleep(10)
    print(f'Failed to retrieve: {xml}.')
    exit(1)
    return False

# --- 2. ORTHOLOGY: THE 4-QUERY APPROACH ---
def fetch_4_way_orthology():
    print("\n[BioMart] Fetching 4-way Orthology matrix...")
    
    # Query 1: Human Source
    q_human = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE Query>
    <Query virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >
        <Dataset name = "hsapiens_gene_ensembl" interface = "default" >
            <Attribute name = "ensembl_gene_id" />
            <Attribute name = "mmusculus_homolog_ensembl_gene" /><Attribute name = "mmusculus_homolog_orthology_type" />
            <Attribute name = "rnorvegicus_homolog_ensembl_gene" /><Attribute name = "rnorvegicus_homolog_orthology_type" />
            <Attribute name = "drerio_homolog_ensembl_gene" /><Attribute name = "drerio_homolog_orthology_type" />
            <Attribute name = "xtropicalis_homolog_ensembl_gene" /><Attribute name = "xtropicalis_homolog_orthology_type" />
        </Dataset>
    </Query>"""
    
    # Query 2: Mouse Source
    q_mouse = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE Query>
    <Query virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >
        <Dataset name = "mmusculus_gene_ensembl" interface = "default" >
            <Attribute name = "ensembl_gene_id" />
            <Attribute name = "rnorvegicus_homolog_ensembl_gene" /><Attribute name = "rnorvegicus_homolog_orthology_type" />
            <Attribute name = "drerio_homolog_ensembl_gene" /><Attribute name = "drerio_homolog_orthology_type" />
            <Attribute name = "xtropicalis_homolog_ensembl_gene" /><Attribute name = "xtropicalis_homolog_orthology_type" />
        </Dataset>
    </Query>"""

    # Query 3: Rat Source
    q_rat = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE Query>
    <Query virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >
        <Dataset name = "rnorvegicus_gene_ensembl" interface = "default" >
            <Attribute name = "ensembl_gene_id" />
            <Attribute name = "drerio_homolog_ensembl_gene" /><Attribute name = "drerio_homolog_orthology_type" />
            <Attribute name = "xtropicalis_homolog_ensembl_gene" /><Attribute name = "xtropicalis_homolog_orthology_type" />
        </Dataset>
    </Query>"""

    # Query 4: Zebrafish Source
    q_fish = """<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE Query>
    <Query virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >
        <Dataset name = "drerio_gene_ensembl" interface = "default" >
            <Attribute name = "ensembl_gene_id" />
            <Attribute name = "xtropicalis_homolog_ensembl_gene" /><Attribute name = "xtropicalis_homolog_orthology_type" />
        </Dataset>
    </Query>"""

    queries = {
        "human_orthology.txt": q_human,
        "mouse_orthology.txt": q_mouse,
        "rat_orthology.txt": q_rat,
        "zebrafish_orthology.txt": q_fish
    }

    for filename, xml in queries.items():
        print(f"  Downloading {filename}...")
        run_biomart_query(xml, os.path.join(ROOT_DIR, filename))

# --- 3. DOMAINS: ENSEMBL XREFS ---
def fetch_ensembl_domains(sp_key):
    ens_map = {"H_sapiens": "hsapiens", "M_musculus": "mmusculus", "R_norvegicus": "rnorvegicus", "D_rerio": "drerio", "X_tropicalis": "xtropicalis"}
    local_dir = os.path.join(ROOT_DIR, sp_key, "ensembl")
    os.makedirs(local_dir, exist_ok=True)
    
    # We download InterPro as the master list, and Pfam/SMART/Tigrfams for specificity
    for attr in ["interpro", "pfam", "smart", "tigrfams"]:
        # 1. Start with the core attributes everyone has
        attr_list = [
            "ensembl_peptide_id",
            "ensembl_transcript_id",
            attr,
            f"{attr}_start",
            f"{attr}_end",
            f"{attr}_description"
        ]
        
        # 2. Add short description ONLY for interpro
        if attr == "interpro":
            attr_list.append("interpro_short_description")
        
        # 3. Convert list to XML Attribute tags
        attribute_xml = "\n".join([f'<Attribute name = "{a}" />' for a in attr_list])

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE Query>
        <Query virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" >
            <Dataset name = "{ens_map[sp_key]}_gene_ensembl" interface = "default" >
                {attribute_xml}
            </Dataset>
        </Query>"""

        run_biomart_query(xml, os.path.join(local_dir, f"{sp_key}.Domains.{attr}.txt"))
      

def query_ensembl_direct(species="homo_sapiens", chromosome="21"):
    # Connection details for Ensembl Public MySQL
    config = {
        'host': 'ensembldb.ensembl.org',
        'port': 3306,
        'user': 'anonymous',
        'database': f'{species}_core_115_38' # Adjust version as needed (115 is current)
    }

    # The SQL query to bridge Ensembl Protein to NCBI and Domains
    sql = f"""
    SELECT 
        g.stable_id AS gene_id,
        t.stable_id AS transcript_id,
        p.stable_id AS protein_id,
        sr.name AS chromosome,
        x.display_label AS xref_id,
        edb.db_name AS database_name
    FROM 
        gene g
        JOIN seq_region sr ON g.seq_region_id = sr.seq_region_id
        JOIN transcript t ON g.gene_id = t.gene_id
        JOIN translation p ON t.transcript_id = p.transcript_id
        LEFT JOIN object_xref ox ON p.translation_id = ox.ensembl_id AND ox.ensembl_object_type = 'Translation'
        LEFT JOIN xref x ON ox.xref_id = x.xref_id
        LEFT JOIN external_db edb ON x.external_db_id = edb.external_db_id
    WHERE 
        sr.name = '{chromosome}' 
        AND edb.db_name IN ('RefSeq_peptide', 'Interpro', 'Pfam', 'Smart')
    """

    try:
        print(f"Connecting to Ensembl for Chromosome {chromosome}...")
        conn = mysql.connector.connect(**config)
        df = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"SQL Error: {e}")
        return None
# both gett_human_mapping_local and download_ensembl_ncbi_mapping() fetches the Ensembl to NCBI mapping
# one uses ftp and the other uses BioMart. The Ensembl FTP mapping is much faster to download and parse,
#  so we use it as the default method. The BioMart method is kept as a backup in case the FTP file is unavailable or outdated.
def get_human_mapping_local() -> pd.DataFrame:
    # Ensembl 115 (Current for 2026) TSV mapping path
    url = "https://ftp.ensembl.org/pub/current_tsv/homo_sapiens/Homo_sapiens.GRCh38.115.entrez.tsv.gz"
    local_file = "human_map.tsv.gz"
    
    print("Downloading high-speed mapping file...")
    with requests.get(url, stream=True) as r:
        with open(local_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
            
    # Load into Pandas (this will take ~2 seconds vs 10 mins for BioMart)
    df = pd.read_csv(local_file, sep='\t', compression='gzip')
    return df

def download_ensembl_ncbi_mapping(species_name="xtropicalis", chromosome="1"):
    """
    Downloads a mapping table for a specific species.
    Common names: 'hsapiens', 'mmusculus', 'rnorvegicus', 'drerio', 'xtropicalis'
    """
    print(f"Fetching mapping for {species_name}...")
    
    # The BioMart XML query: asking for Ensembl IDs + NCBI RefSeq IDs
    xml_query = f"""<?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE Query>
    <Query virtualSchemaName="default" formatter="TSV" header="1" uniqueRows="1" count="" datasetConfigVersion="0.6">
        <Dataset name="{species_name}_gene_ensembl" interface="default">
            
            <Filter name="chromosome_name" value="{chromosome}"/>
            
            <Attribute name="ensembl_gene_id" />
            <Attribute name="ensembl_peptide_id" />
            <Attribute name="refseq_peptide" />     
        </Dataset>
    </Query>""".strip()
    # <Attribute name="interpro" />
    #        <Attribute name="pfam" />
    #        <Attribute name="smart" />
    url = "http://www.ensembl.org/biomart/martservice"
    response = requests.get(url, params={'query': xml_query})
    
    if response.status_code == 200:
        df = pd.read_csv(StringIO(response.text), sep='\t')
        # Clean up: Remove rows where no NCBI mapping exists
        #df = df.dropna(subset=['RefSeq mRNA ID', 'RefSeq peptide ID'], how='all')
        return df
    else:
        print(f"Error: {response.status_code}")
        return None



def parse_species_args(species_str):
    """Convert species arguments (including shortcuts) to full species keys.
    
    Args:
        species_str: Comma-separated string of species (e.g., 'H,M,R' or 'H_sapiens,M_musculus')
    """
    # Split by comma and strip whitespace
    species_list = [s.strip() for s in species_str.split(',')]
    
    if not species_list or 'all' in [s.lower() for s in species_list]:
        return list(SpeciesConvention.keys())
    
    resolved = []
    for s in species_list:
        if not s:  # Skip empty strings
            continue
        # Check if it's a shortcut
        if s.upper() in SPECIES_SHORTCUTS:
            resolved.append(SPECIES_SHORTCUTS[s.upper()])
        # Check if it's a full species key
        elif s in SpeciesConvention:
            resolved.append(s)
        else:
            print(f"Warning: Unknown species '{s}', skipping.")
    
    return resolved

def setup_argument_parser():
    """Setup and return the argument parser for the script."""
    parser = argparse.ArgumentParser(
        description='Download genomic data from NCBI and/or Ensembl',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --species H,M                       # Download Human and Mouse, fetch orthology
  %(prog)s --species all --source ncbi         # Download all species from NCBI only
  %(prog)s -s H_sapiens -o ./data              # Download Human to ./data directory
  %(prog)s -s H,M --no-orthology               # Download without orthology data
        """)
    
    parser.add_argument('-o', '--output-dir', 
                        default='./genomic_data',
                        help='Output directory for downloaded files (default: ./genomic_data)')
    
    parser.add_argument('-s', '--species', 
                        default='all',
                        help='Comma-separated list of species to download. Use shortcuts (H, M, R, D, X) '
                             'or full names (H_sapiens, M_musculus, R_norvegicus, D_rerio, X_tropicalis). '
                             'Examples: "H,M" or "H_sapiens,M_musculus". Default: all')
    
    parser.add_argument('--source',
                        choices=['ncbi', 'ensembl', 'both'],
                        default='both',
                        help='Data source to download from (default: both)')
    
    parser.add_argument('--no-orthology',
                        dest='fetch_orthology',
                        action='store_false',
                        default=True,
                        help='Skip orthology data fetching (default: fetch orthology when using Ensembl source with multiple species)')
    
    return parser

def main():
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Parse output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Parse species
    species_to_process = parse_species_args(args.species)
    
    if not species_to_process:
        print("Error: No valid species specified.")
        return
    
    print(f"Processing species: {', '.join(species_to_process)}")
    print(f"Sources: {args.source}")
    print(f"Output directory: {output_path}\n")
    
    # Download data for each species
    for species in species_to_process:
        if args.source in ['ncbi', 'both']:
            download_ncbi(species, output_dir=output_path / species / "refseq")
        
        if args.source in ['ensembl', 'both']:
            download_ensembl_gff(species, output_dir=output_path / species / "ensembl")
    
    # Fetch orthology data
    # Fetch if flag is True, Ensembl is a source, and multiple species
    should_fetch_orthology = (
        args.fetch_orthology and 
        args.source in ['ensembl', 'both'] and 
        len(species_to_process) > 1
    )
    
    if should_fetch_orthology:
        print("\nFetching orthology data...")
        fetch_4_way_orthology()

if __name__ == "__main__":
    main()
