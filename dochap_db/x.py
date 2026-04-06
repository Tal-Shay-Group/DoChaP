from Bio import Entrez, SeqIO

import requests
from tqdm import tqdm  # Optional: for a nice progress bar

def download_interpro_mapping(output_path="protein2ipr.dat.gz"):
    url = "https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/protein2ipr.dat.gz"

    # Send a streaming request
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Check for HTTP errors

    # Get file size for the progress bar
    total_size = int(response.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte

    print(f"Downloading to {output_path}...")
    with open(output_path, 'wb') as file:
        for data in response.iter_content(block_size):
            file.write(data)

    print("Download complete.")

# Run the downloader
Entrez.email = "your_email@example.com"

def get_domains(refseq_id):
    # Fetch the GenBank record for the protein
    handle = Entrez.efetch(db="protein", id=refseq_id, rettype="gb", retmode="text")
    record = SeqIO.read(handle, "genbank")
    
    for feature in record.features:
        if feature.type == "Region":
            name = feature.qualifiers.get("region_name", ["Unknown"])[0]
            db_xref = feature.qualifiers.get("db_xref", [])
            print(f"Domain: {name} | Range: {feature.location} | Source: {db_xref}")

#get_domains("NP_001087.2")
download_interpro_mapping()
