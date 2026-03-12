import os
from pathlib import Path
import requests
import re
import gzip
import shutil
import time
import sys
from ftplib import FTP


def get_ncbi_latest_release(species):
    # 1. Clean the name for a broad search
    species_query = species.replace("_", "+")
    
    # 2. Search for ANY assembly associated with this name (no filters yet)
    # We remove [Organism] and [filter] to see what NCBI actually has
    search_url = (
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?"
        f"db=assembly&term={species_query}&retmode=json&retmax=10"
    )
    
    try:
        r = requests.get(search_url, timeout=30)
        r.raise_for_status()
        asm_ids = r.json().get('esearchresult', {}).get('idlist', [])
        
        if not asm_ids:
            raise Exception(f"NCBI found zero records for query: {species_query}")
        
        # 3. Get summaries for all found IDs and look for the RefSeq (GCF) version
        summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=assembly&id={','.join(asm_ids)}&retmode=json"
        s_res = requests.get(summary_url).json()
        
        for aid in asm_ids:
            details = s_res['result'][aid]
            accession = details.get('assemblyaccession', '')
            
            # We want the RefSeq version (starts with GCF)
            if accession.startswith("GCF"):
                official_name = details.get('speciesname', 'Unknown')
                print(f"Match Found!")
                print(f"  Input: {species}")
                print(f"  Official Name: {official_name}")
                print(f"  Accession: {accession}")
                return accession
                
        raise Exception(f"Found assemblies for {species}, but none were RefSeq (GCF).")

    except Exception as e:
        print(f"Search Error: {e}")
        raise


def download_ncbi_gff(species, release='latest', output_dir="."):
    """
    Downloads GFF3 from NCBI RefSeq with robust search logic.
    """
    # 1. Clean the species name for NCBI (e.g., Xenopus_tropicalis -> "Xenopus tropicalis")
    species_clean = species.replace("_", " ")
    
    if release == 'latest':
        accession = get_ncbi_latest_release(species)
    else:
        # If user provided a specific GCF_... accession
        accession = release

    # 3. Construct the Triplet FTP Path
    # GCF_000004195.4 -> parts: ['000', '000', '419', '5'] (example logic)
    # Correct NCBI triplet logic:
    acc_num = accession.split('_')[1].split('.')[0]
    f1, f2, f3 = acc_num[0:3], acc_num[3:6], acc_num[6:9]
    base_url = f"https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/{f1}/{f2}/{f3}/"

    # 4. Find the full folder name (it includes the assembly name)
    try:
        dir_listing = requests.get(base_url, timeout=30).text
        # Look for the folder starting with our accession
        folder_match = re.search(fr'({accession}[^/"]+)/', dir_listing)
        if not folder_match:
            raise Exception(f"Could not find folder for {accession} at {base_url}")
        
        full_folder = folder_match.group(1)
        file_name = f"{full_folder}_genomic.gff.gz"
        file_url = f"{base_url}{full_folder}/{file_name}"
        
        # 5. Download the file
        dest_path = os.path.join(output_dir, file_name)
        print(f"NCBI Match: {accession}")
        print(f"Downloading: {file_url}")
        
        with requests.get(file_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    f.write(chunk)
                    
        print(f"Done: {dest_path}")
        return dest_path

    except Exception as e:
        print(f"Download error: {e}")
        return None


def download_ensembl_gff(species, release='latest', output_dir="."):
    """
    Downloads GFF3 from Ensembl. 
    Fixes 404 errors by scraping the directory for the exact filename casing.
    """
    if species not in ENSEMBL_SPECIES_INFO:
        print(f"  Error: Species {species} not configured for Ensembl download")
        return None
    
    species_info = ENSEMBL_SPECIES_INFO[species]
    species_name = species_info["name"]
    
    local_dir = Path(ROOT_DIR) / species / "ensembl"
    local_dir.mkdir(parents=True, exist_ok=True)
    # 1. Folder names in the URL path are ALWAYS lowercase
    species_folder = species_name.lower()
    
    # 2. Determine the release number
    if release == 'latest':
        try:
            r_info = requests.get("https://rest.ensembl.org/info/software?content-type=application/json", timeout=30)
            r_info.raise_for_status()
            release_num = r_info.json()['release']
        except:
            release_num = 115 # Fallback if API is down
    else:
        release_num = release

    # 3. Define the directory URL
    base_ftp = f"https://ftp.ensembl.org/pub/release-{release_num}/gff3/{species_folder}/"
    
    print(f"Connecting to Ensembl directory: {base_ftp}")
    
    try:
        # Request the directory listing (the HTML page showing the list of files)
        response = requests.get(base_ftp, timeout=60)
        response.raise_for_status()
        
        # 4. SCRAPE the actual filenames from the HTML
        # This grabs the exact casing used on the server (e.g., lowercase 't' in tropicalis)
        links = re.findall(r'href="([^"]+\.gff3\.gz)"', response.text)
        
        # 5. Filter for the "Primary" genomic file
        # We exclude 'chr' (individual chromosomes), 'abinitio', and 'semimanaged'
        target_file = None
        for link in links:
            # Must contain the release number and NOT contain specific keywords
            if str(release_num) in link:
                if not any(x in link.lower() for x in ['chr.', 'abinitio', 'semimanaged', 'chr_patch']):
                    target_file = link
                    break
        
        if not target_file:
            raise FileNotFoundError(f"Could not find a primary GFF3 file in {base_ftp}")

        # 6. Build the final URL using the EXACT string found on the server
        file_url = base_ftp + target_file
        dest_path = os.path.join(output_dir, target_file)

        print(f"Verified filename found: {target_file}")
        print(f"Downloading from: {file_url}")
        
        with requests.get(file_url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
                    
        print(f"Successfully downloaded: {dest_path}")
        return dest_path

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}. Check if species '{species_folder}' exists in release {release_num}.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


# --- CONFIGURATION ---
# Update these GCF IDs manually as NCBI releases new patches
ASSEMBLY_VERSIONS = {
    "H_sapiens": "GCF_000001405.40",
    "M_musculus": "GCF_000001635.27",
    "R_norvegicus": "GCF_015227675.2",
    "D_rerio": "GCF_000002035.6",
    "X_tropicalis": "GCF_000004195.4"
}

ROOT_DIR = Path("./genomic_data")
BIOMART_URL = "http://www.ensembl.org/biomart/martservice"
MAX_RETRIES = 5
ENSEMBL_RELEASE = "115"  # Update as Ensembl releases new versions

# Ensembl species mapping with assembly versions
ENSEMBL_SPECIES_INFO = {
    "H_sapiens": {"name": "homo_sapiens", "assembly": "GRCh38"},
    "M_musculus": {"name": "mus_musculus", "assembly": "GRCm39"},
    "R_norvegicus": {"name": "rattus_norvegicus", "assembly": "mRatBN7.2"},
    "D_rerio": {"name": "danio_rerio", "assembly": "GRCz11"},
    "X_tropicalis": {"name": "xenopus_tropicalis", "assembly": "UCB_Xtro_10.0"}
}

def download_refseq(sp_key, gcf_id):
    print(f"\n[NCBI] Processing {sp_key} ({gcf_id})...")
    local_dir = ROOT_DIR / sp_key / "refseq"
    local_dir.mkdir(parents=True, exist_ok=True)

    # GCF_000001405.40 -> 000/001/405
    num = gcf_id.split('_')[1].split('.')[0]
    prefix = "/".join([num[i:i+3] for i in range(0, len(num), 3)])

    for attempt in range(MAX_RETRIES):
        try:
            with FTP("ftp.ncbi.nlm.nih.gov", timeout=60) as ftp:
                ftp.login()
                ftp.set_pasv(True) # CRITICAL for Errno 111 fix

                ftp.cwd(f"/genomes/all/GCF/{prefix}")
                folders = [f for f in ftp.nlst() if f.startswith(gcf_id)]
                if not folders: return

                ftp.cwd(folders[0])
                files = ftp.nlst()

                targets = {
                    "gff": [f for f in files if f.endswith("_genomic.gff.gz")][0],
                    "gpff": [f for f in files if f.endswith("_protein.gpff.gz")][0]
                }

                for label, filename in targets.items():
                    local_path = local_dir / filename
                    print(f"  Downloading {label}: {filename}...")
                    with open(local_path, "wb") as f:
                        ftp.retrbinary(f"RETR {filename}", f.write)

                    # Decompressing for DoChaPBuilder
                    print(f"  Extracting {label}...")
                    with gzip.open(local_path, 'rb') as f_in:
                        with open(str(local_path).replace('.gz', ''), 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    local_path.unlink()
                break
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(10)
            else:
                raise

def download_refseq_https(sp_key, gcf_id):
    print(f"\n[NCBI-HTTPS] Processing {sp_key} ({gcf_id})...")
    local_dir = Path(ROOT_DIR) / sp_key / "refseq"
    local_dir.mkdir(parents=True, exist_ok=True)

    # 1. Format the URL for the HTTPS mirror
    # NCBI HTTPS mirror follows the same path structure as FTP
    num = gcf_id.split('_')[1].split('.')[0]
    prefix = "/".join([num[i:i+3] for i in range(0, len(num), 3)])

    # Base URL for the assembly's parent folder
    base_url = f"https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/{prefix}"

    # 2. Since we can't 'nlst' easily on HTTPS without parsing HTML,
    # we use a trick: the 'latest_assembly_versions' or assembly reports.
    # However, since you have the GCF ID, we can often predict the folder name
    # OR use the 'all' directory search.

    # Robust way: Get the directory listing via requests (NCBI provides an index page)
    try:
        r = requests.get(base_url, timeout=30)
        r.raise_for_status()

        # Use regex to find the specific folder matching your GCF ID
        import re
        folder_match = re.search(f'({gcf_id}_[^/"]+)', r.text)
        if not folder_match:
            print(f"  Error: Could not find folder for {gcf_id}")
            return

        full_folder_name = folder_match.group(1)
        final_url = f"{base_url}/{full_folder_name}"
        print(f"  Found folder: {full_folder_name}")

        # 3. Define target files
        # Files are named: {folder_name}_genomic.gff.gz
        targets = {
            "gff": f"{full_folder_name}_genomic.gff.gz",
            "gpff": f"{full_folder_name}_protein.gpff.gz"
        }

        for label, filename in targets.items():
            file_url = f"{final_url}/{filename}"
            local_path = local_dir / filename

            print(f"  Downloading {label} via HTTPS...")
            with requests.get(file_url, stream=True, timeout=60) as stream_r:
                stream_r.raise_for_status()
                with open(local_path, 'wb') as f:
                    for chunk in stream_r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # Decompress
            print(f"  Extracting {filename}...")
            with gzip.open(local_path, 'rb') as f_in:
                with open(str(local_path).replace('.gz', ''), 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            local_path.unlink()

    except Exception as e:
        print(f"  HTTPS Download Failed: {e}")
        raise


def download_ensembl_gff_wrapper(sp_key, release='latest'):
    """
    Wrapper function to download Ensembl GFF3 for a species key.
    Uses the existing download_ensembl_gff function with proper parameters.
    """
    if sp_key not in ENSEMBL_SPECIES_INFO:
        print(f"  Error: Species {sp_key} not configured for Ensembl download")
        return None
    
    species_info = ENSEMBL_SPECIES_INFO[sp_key]
    species_name = species_info["name"]
    
    local_dir = Path(ROOT_DIR) / sp_key / "ensembl"
    local_dir.mkdir(parents=True, exist_ok=True)
    
    # Call the existing robust download function
    result = download_ensembl_gff(species_name, release=release, output_dir=str(local_dir))
    
    # Decompress if download was successful
    if result and os.path.exists(result):
        print(f"  Extracting GFF3...")
        decompressed_path = result.replace('.gz', '')
        try:
            with gzip.open(result, 'rb') as f_in:
                with open(decompressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(result)
            print(f"  Completed: {sp_key} GFF3 extraction")
            return decompressed_path
        except Exception as e:
            print(f"  Extraction failed: {e}")
            return result
    
    return result


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
      


def main():
    path = ROOT_DIR
    path.mkdir(parents=True, exist_ok=True)
    download_ncbi_gff("Xenopus_tropicalis")
    download_ensembl_gff("X_tropicalis")
    return
    #fetch_4_way_orthology()
    for sp_key, gcf_id in ASSEMBLY_VERSIONS.items():
        download_refseq_https(sp_key, gcf_id)
        download_ensembl_gff_wrapper(sp_key)
        fetch_ensembl_domains(sp_key)

if __name__ == "__main__":
    main()
