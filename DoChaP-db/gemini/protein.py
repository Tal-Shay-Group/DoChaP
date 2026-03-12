import gffutils
import sqlite3
import sys
import os
from Bio import SeqIO
import time

def save_memory_db_to_disk(gffutils_db, output_path):
    # Connect to a new physical file
    dest = sqlite3.connect(output_path)
    # Access the underlying sqlite connection from gffutils
    source = gffutils_db.conn

    print(f"Saving memory DB to {output_path}...")
    with dest:
        source.backup(dest) # Efficiently streams memory to disk
    dest.close()

def gpff_to_gff3(gpff_file, output_gff):
    print(f'starting gpff_to_gff3 {gpff_file} -> {{output_gff}')
    start = time.time()
    with open(output_gff, "w") as out:
        out.write("##gff-version 3\n")
        for record in SeqIO.parse(gpff_file, "genbank"):
            # Create a GFF3 row for the protein
            # Format: seqid, source, type, start, end, score, strand, phase, attributes
            attributes = f"ID={record.id};Name={record.name};product={record.description}"
            if record.dbxrefs:
                attributes += f";Dbxref={','.join(record.dbxrefs)}"
            
            # Since GPFF doesn't have genomic coords, we use 1 to length as a placeholder
            row = f"{record.id}\tGenBank\tprotein\t1\t{len(record.seq)}\t.\t.\t.\t{attributes}\n"
            out.write(row)
    print(f'Done gpff_to_gff3 {gpff_file} -> {{output_gff}. {start - time.time()}')

def gff2db(gff_file, db_file):
    print(f'Starting gff2db {gff_file} => {db_file}')
    start = time.time()
    db = gffutils.create_db(
        gff_file,
        dbfn=':memory:',           # Store in RAM, no disk writing
        force=True,
        merge_strategy='merge',
        keep_order=False,         # Assumes file is already sorted (Ensembl/NCBI are)
        disable_infer_genes=True,  # Don't try to "guess" gene lines
        disable_infer_transcripts=True, # Don't try to "guess" transcript lines
        id_spec='ID'               # Standard for NCBI/Ensembl GFFs
    )
    save_memory_db_to_disk(db, db_file)
    print(f'Done gff2db {gff_file} => {db_file}. {time.time()- start}')
    return db

def explore(db_file):
    db = gffutils.FeatureDB(db_file)
    # 1. See what types of features were parsed
    print("Feature types in DB:", list(db.featuretypes()))

    # 2. Inspect the first 5 proteins
    for protein in db.all_features(limit=5):
        print(f"ID: {protein.id}")
        print(f"Attributes: {dict(protein.attributes)}")
        print("-" * 20)


def main():
    gpff_file = sys.argv[1]
    gff_file = sys.argv[1] + ".gff"
    db_file = gpff_file + ".db"
    gpff_to_gff3(gpff_file, gff_file)
    gff2db(gff_file, db_file)
    explore(db_file)

main()
