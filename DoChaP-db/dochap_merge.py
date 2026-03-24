import shutil
import sys
import time
import os
import glob
import re
import logging
from typing import Optional, Tuple
import pandas as pd
import numpy as np
import sqlite3
from Bio import SeqIO
import gzip
import gffutils
from dochap_definition import DoChaPDB
from pathlib import Path
import dochap_parse_protein_gpff
# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class DoChaPCMerger:
    def __init__(self, ncbi_gff, ensembl_gff, species, 
                 ncbi_gpff_pattern, interpro_domain_file, db_out="unified_genome.db", print_interval=60):
        logger
        # Initialize gffutils databases (in-memory for speed if files aren't massive)
        self.domain_type_map = {}  # Map between reg hash to id
        self.transcript_map = {} # {t_id: {'offset': int, 'exons': [(abs_s, abs_e, idx)]}}
        self.transcript_refseq2ensembl = {} # {refseq_tx_id: ensembl_tx_id}
        self.print_interval = print_interval
        self.species = species
        self.domain_type_counter = 0
        
        self.interpro_domain_file = interpro_domain_file
        if str(ensembl_gff).endswith('.gz'):
            self.ensembl_gff = self.decompress_gff(str(ensembl_gff))
        else:
            self.ensembl_gff = str(ensembl_gff)
        if str(ncbi_gff).endswith('.gz'):
            self.ncbi_gff = self.decompress_gff(str(ncbi_gff))
        else:
            self.ncbi_gff = str(ncbi_gff)
        self.n_db = self.gff_to_sqlite(self.ncbi_gff, self.ncbi_gff + ".db")
        self.e_db = self.gff_to_sqlite(self.ensembl_gff, self.ensembl_gff + ".db")
        self.ncbi_gpff_files = glob.glob(str(ncbi_gpff_pattern))
        if not self.ncbi_gpff_files:
            logger.error(f"No GPFF files found matching pattern: {ncbi_gpff_pattern}")
            sys.exit(1)
        self.ncbi_gpff_files.sort()
        logger.info(f"NCBI GFF: {self.ncbi_gff}")
        logger.info(f"Ensembl GFF: {self.ensembl_gff}")
        for f in self.ncbi_gpff_files:
            logger.info(f"  NCBI GPFF file: {f}")

        # 2. Setup Unified SQL Database
        self.output_db = DoChaPDB(db_out)
        self.output_db.connect()
        logger.info(f"Initialized output database at {db_out}")

    def clean_id(self, identifier):
        if not identifier or pd.isna(identifier) or identifier == "": 
            return ''
        id = str(identifier)
        tags = ['gene-', 'rna-', 'transcript-', 'protein-', 'gene:', 'rna:', 'transcript:', 'protein:', 'CDS:']
        for tag in tags:
            if tag in id:
                return id.removeprefix(tag)#.split('.')[0]  # Remove version suffix if present
        return id#.split('.')[0]  # Remove version suffix if present

    def is_gene_protein_coding(self, gene):
        biotype = gene.attributes.get('gene_biotype', gene.attributes.get('biotype', [None]))[0]
        if biotype in ['protein_coding', 'protein-coding']:
            return True
        return False

    def decompress_gff(self, input_file):
        # Determine output name (remove .gz)
        output_file = input_file.replace('.gz', '')
        if os.path.exists(output_file):
            logger.info(f"Decompressed file {output_file} already exists. Skipping decompression.")
            return output_file
        logger.info(f"Decompressing {input_file}...")
        os.system(f'gunzip -k -f {input_file}')
        logger.info(f"Decompression complete: {output_file}")
        return output_file

    def save_memory_db_to_disk(self, gffutils_db, output_path):
        # Connect to a new physical file
        dest = sqlite3.connect(output_path)
        # Access the underlying sqlite connection from gffutils
        source = gffutils_db.conn 

        logger.info(f"Saving memory DB to {output_path}...")
        with dest:
            source.backup(dest) # Efficiently streams memory to disk
        dest.close()

    def gff_to_sqlite(self, gff_file, db_file):
        start_time = time.time()

        if os.path.exists(db_file):
            logger.info(f"Database {db_file} already exists. Loading...")
            return gffutils.FeatureDB(db_file, keep_order=True, sort_attribute_values=True)

        # Create a gffutils database from the GFF file
        logger.info(f"Creating gffutils database from {gff_file}...")
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
        self.save_memory_db_to_disk(db, db_file)  # Save the in-memory DB to disk for future use
        logger.info(f"Database created at {db_file}, duration: {time.time() - start_time:.2f} seconds")
        return db

    def get_gene_synonyms(self, e_gene, n_gene):
        synonyms = n_gene.attributes.get('Alias', []) if n_gene else []
        synonyms += n_gene.attributes.get('gene_synonym', []) if n_gene else []
        synonyms += e_gene.attributes.get('Alias', []) if e_gene else []
        synonyms += e_gene.attributes.get('external_name', []) if e_gene else []
        synonyms += e_gene.attributes.get('gene_synonym', []) if e_gene else []
        return list(set(synonyms))  # Remove duplicates

    def build_gene_name_index(self, db):
        """Build a dictionary mapping gene names to gene features"""
        index = {}
        for gene in db.features_of_type('gene'):
            # Try different attribute keys
            name = gene.attributes.get('Name', [None])[0]
            symbol = gene.attributes.get('gene', [None])[0]
            
            for key in [name, symbol]:
                if key:
                    index[key] = gene
        return index

    def match_gene(self, e_db_index, e_db, symbol, n_gene_id, ensembl_id, n_gene):
        match_method = "x"
        e_gene = None
        if symbol:
            e_gene = e_db_index.get(symbol, None)
            if e_gene:
                match_method = "Symbol"
        elif not e_gene and n_gene_id:
            e_gene = e_db_index.get(n_gene_id, None)
            if e_gene:
                match_method = "NCBI_id"
        if not e_gene and ensembl_id:
            e_gene = e_db_index.get(ensembl_id, None)
            if e_gene:
                match_method = "ensembl_id"
        return e_gene, match_method

    def get_exon_fingerprint(self, db, transcript):
        """Creates a unique string based on all exon coordinates for a transcript."""
        exons = list(db.children(transcript, featuretype='exon', order_by='start'))
        # Fingerprint format: "start-end|start-end|..."
        return "|".join([f"{e.start}-{e.end}" for e in exons]) 

    def add_missing_ensembl_genes(self, e_gene_handled_ids):
        count = 0  
        count_alternative = 0
        count_non_coding = 0
        for e_gene in self.e_db.features_of_type('gene'):
            if not self.is_primary_chromosome(self.e_db, self.clean_id(e_gene.seqid)):
                logger.debug(f"Skipping alternative chromosome {e_gene.seqid} for gene {e_gene.id}")
                count_alternative += 1
                continue
            if not self.is_gene_protein_coding(e_gene):
                logger.debug(f"Skipping non-protein-coding gene {e_gene.id} ({e_gene.attributes.get('Name', [''])[0]})")
                count_non_coding += 1
                continue
            ensembl_id = self.clean_id(e_gene.id)
            if ensembl_id in e_gene_handled_ids:
                logger.debug(f"Already handled Ensembl gene {ensembl_id} from NCBI match, skipping.")
                continue
            synonyms = ";".join(self.get_gene_synonyms(e_gene, None))
            symbol = e_gene.attributes.get('Name', [''])[0]
            self.output_db.add_row('Genes', (None, ensembl_id, symbol, synonyms, e_gene.seqid, e_gene.strand, self.species))
            logger.info(f"Added missing Ensembl gene {ensembl_id} with symbol {symbol} on {e_gene.seqid} to output database.")
            self.add_transcripts('', None, e_gene)
        logger.info(f"Processed {count} Ensembl genes. Skipped {count_alternative} on alternative chromosomes and {count_non_coding} non-protein-coding genes.")
    
    def refseq_gene_id(self, n_gene):
        dbxrefs = n_gene.attributes.get('Dbxref', [])
        return next((x.split(':')[1] for x in dbxrefs if 'GeneID' in x), '')
        
    def map_genes_transcripts_proteins(self):
        e_db_index = self.build_gene_name_index(self.e_db)  # Build an index for quick name-based lookups in Ensembl
        self.genes_e2n = {}
        self.transcripts_e2n = {}
        self.proteins_e2n = {}
        counter = 0
        last_print_time = time.time()
        msg = "Mapping NCBI genes to Ensembl: "
        for n_gene in self.n_db.features_of_type('gene'):
            counter , last_print_time = self.track_progress(counter, last_print_time, msg)
            ensembl_id = self.get_dbxref_ensemble_id(n_gene)
            if not ensembl_id:
                symbol = n_gene.attributes.get('gene', [None])[0]
                name = n_gene.attributes.get('Name', [''])[0]
                e_gene, match_method = self.match_gene(e_db_index, self.e_db, symbol, name, ensembl_id, n_gene)
                if e_gene:
                    ensembl_id = self.get_ensemble_id(e_gene)
            if ensembl_id:
                self.genes_e2n[ensembl_id] = n_gene
                for n_tx in self.n_db.children(n_gene.id, featuretype=['transcript', 'mRNA']):
                    if not self.is_protein_coding(self.n_db, n_tx):
                        continue
                    n_tx_id = self.clean_id(n_tx.id)
                    ensembl_id = self.get_dbxref_ensemble_id(n_tx)  
                    if ensembl_id:
                        self.transcripts_e2n[ensembl_id] = n_tx_id
        counter = 0
        last_print_time = time.time()
        msg = "Mapping NCBI proteins to Ensembl: "
        for n_protein in self.n_db.features_of_type('CDS'):
            counter , last_print_time = self.track_progress(counter, last_print_time, msg)
            ensembl_id = self.get_dbxref_ensemble_id(n_protein)  
            if ensembl_id:
                self.proteins_e2n[ensembl_id] = n_protein
        

    def traverse_ensembl(self):
        self.map_genes_transcripts_proteins()
        counter = 0
        last_print_time = time.time()
        msg = f"Processing Ensembl genes: "
        for e_gene in self.e_db.features_of_type('gene'):
            counter , last_print_time = self.track_progress(counter, last_print_time, msg)
            ensembl_id = self.get_ensemble_id(e_gene)
            symbol = e_gene.attributes.get('Name', [''])[0]
            logger.debug(f"Traversing Ensembl gene {ensembl_id} (symbol: {symbol}) on {e_gene.seqid}:{e_gene.start}-{e_gene.end}")
            if not self.is_primary_chromosome(self.e_db, self.clean_id(e_gene.seqid)):
                logger.debug(f"Skipping alternative chromosome {e_gene.seqid} for gene {ensembl_id}")
                continue
            if not self.is_gene_protein_coding(e_gene):
                logger.debug(f"Skipping non-protein-coding gene {ensembl_id}, {symbol})")
                continue
            n_gene = self.genes_e2n.get(ensembl_id, None)
            n_gene_id = self.refseq_gene_id(n_gene) if n_gene else None
            synonyms = ";".join(self.get_gene_synonyms(e_gene, n_gene))
            self.output_db.add_row('Genes', (n_gene_id, ensembl_id, symbol, synonyms, e_gene.chrom, e_gene.strand, self.species))
            logger.info(f"Added Ensembl gene {ensembl_id} with symbol {symbol} on {e_gene.chrom} to output database.")
            self.add_ensembl_transcripts(e_gene) 
        self.output_db.flush_buffers(force=True) 

                

    def traverse_ncbi_genes(self):
        logger.info(f"Traversing NCBI genes")
        chrom_ncbi2ensembl_map = {}  # Map NCBI chromosome names to Ensembl chromosome names for spatial matching
        count = 0
        count_alternative = 0
        count_non_coding = 0
        count_matches = 0
        e_gene_handled_ids = set()
        e_db_index = self.build_gene_name_index(self.e_db)  # Build an index for quick name-based lookups in Ensembl
        for n_gene in self.n_db.features_of_type('gene'):
            count += 1
            dbxrefs = n_gene.attributes.get('Dbxref', [])
            n_gene_id = next((x.split(':')[1] for x in dbxrefs if 'GeneID' in x), None)  
            symbol = n_gene.attributes.get('gene', [None])[0]
            x_name = n_gene.attributes.get('Name', [''])[0]
            logger.debug(f"Processing NCBI gene {n_gene_id} (symbol: {symbol}, name: {x_name}) on {n_gene.seqid}:{n_gene.start}-{n_gene.end}, count: {count}")
            if count % 1000 == 0:
                logger.info(f"Processed {count} genes...")
            if not self.is_primary_chromosome(self.n_db, self.clean_id(n_gene.seqid)):
                logger.debug(f"Skipping alternative chromosome {n_gene.seqid} for gene {n_gene_id}")
                count_alternative += 1
                continue
            if not self.is_gene_protein_coding(n_gene):    
                logger.debug(f"Skipping non-protein-coding gene {n_gene_id}, {symbol})")
                count_non_coding += 1
                continue
            
            chrom_name = chrom_ncbi2ensembl_map.get(n_gene.chrom, n_gene.chrom)
            ensembl_id = self.get_dbxref_ensemble_id(n_gene)
            e_gene, match_method = self.match_gene(e_db_index, self.e_db, symbol, x_name, ensembl_id, n_gene)
            
            if e_gene:
                ensembl_id = self.get_ensemble_id(e_gene)
                synonyms = ";".join(self.get_gene_synonyms(e_gene, n_gene))
                e_gene_handled_ids.add(ensembl_id)
                chrom_name = e_gene.chrom
                if chrom_name not in chrom_ncbi2ensembl_map:
                    chrom_ncbi2ensembl_map[n_gene.chrom] = chrom_name
                    logger.debug(f"Mapping NCBI chromosome {n_gene.chrom} to Ensembl chromosome {chrom_name} for spatial matching.")
            else:
                ensembl_id = ''  # No Ensembl match
                synonyms = ";".join(self.get_gene_synonyms(None, n_gene))
            
            self.output_db.add_row('Genes', (n_gene_id, ensembl_id, symbol, synonyms, chrom_name, n_gene.strand, self.species))
            logger.info(f"Added gene {n_gene_id} with Ensembl ID {ensembl_id} and symbol {symbol}, chrom {chrom_name} to output database.")
            self.add_transcripts(n_gene_id, n_gene, e_gene) 
            count_matches += 1
        self.output_db.flush_buffers(force=True)
        logger.info(f"\tSkipped {count_alternative} genes on alternative chromosomes.")
        logger.info(f"\tSkipped {count_non_coding} non-protein-coding genes.")
        logger.info(f"\tTotal genes processed: {count-count_alternative-count_non_coding} (matches: {count_matches})")
        return e_gene_handled_ids

    def create_db(self):
        #e_gene_handled_ids = self.traverse_ncbi_genes()        
        #self.add_missing_ensembl_genes(e_gene_handled_ids)
        self.traverse_ensembl()
        self.output_db.flush_buffers(force=True)
        self.output_db.commit()

        self.process_refseq_protein_gpff_files()
        self.output_db.create_index()
        self.output_db.close()
                
        logger.info(f"Merging {self.species} complete.")
        

    def is_protein_coding(self, db, transcript):
        # Count how many CDS features belong to this transcript
        biotype = transcript.attributes.get('biotype', [])
        if biotype and 'protein_coding' not in biotype:
            return False
        cds_count = len(list(db.children(transcript, featuretype='CDS')))
        return cds_count > 0

    def calc_transcript_cds_length(self, db, transcript):
        cds_list = list(db.children(transcript, featuretype='CDS'))
        length = sum(abs(c.start - c.end) + 1 for c in cds_list)
        return length

    def calculate_cds_boundaries(self, transcript, cds_list, exons, cds_min, cds_max):
        if len(cds_list) == 0:
            return [], []  
        abs_start = []
        abs_stop = []
        is_negative = transcript.strand == '-'

        # Handle Strand Direction
        if is_negative:
            exons = exons[::-1]
        current_protein_len = 0

        # 4. Process each exon
        for exon in exons:
            # Clip the exon to the CDS boundaries
            # This effectively removes the 5' and 3' UTRs
            coding_start = max(exon.start, cds_min)
            coding_end = min(exon.end, cds_max)

            # Check if this exon contains any coding sequence
            if coding_start <= coding_end:
                # Calculate length of the coding portion of this exon
                # +1 because coordinates are inclusive (e.g., 100 to 100 is 1bp)
                exon_coding_len = (coding_end - coding_start) + 1
                
                # Start is 1-based relative to the total coding sequence
                abs_start.append(current_protein_len + 1)
                abs_stop.append(current_protein_len + exon_coding_len)
                
                # Update the running total for the next exon
                current_protein_len += exon_coding_len
            else:
                # This is a non-coding exon (entirely 5' or 3' UTR)
                abs_start.append(0)
                abs_stop.append(0)          
        return abs_start, abs_stop

    def add_protein(self, e_tx, n_tx, length):
        e_tx_id = self.get_ensemble_id(e_tx) if e_tx else ''
        n_tx_id = self.clean_id(n_tx.id) if n_tx else ''
        e_protein_id = ''
        n_protein_id = ''
        decription = ''
        synonyms = []
        if e_tx:
            e_cds_list = list(self.e_db.children(e_tx, featuretype='CDS', order_by='start'))
            if e_cds_list:
                cds = e_cds_list[0]
                decription = cds.attributes.get('product', [''])[0]
                synonyms.extend(cds.attributes.get('Alias', []))
                e_protein_id = self.get_ensemble_id(e_cds_list[0])    
        if n_tx:    
            n_cds_list = list(self.n_db.children(n_tx, featuretype='CDS', order_by='start'))
            if n_cds_list:
                cds = n_cds_list[0]
                decription = cds.attributes.get('product', [''])[0]
                synonyms.extend(cds.attributes.get('Alias', []))
                n_protein_id = self.clean_id(n_cds_list[0].attributes.get('protein_id', [''])[0])
        synonyms = np.unique(synonyms)
        if n_protein_id != '' or e_protein_id != '':
            # protein_refseq_id, protein_ensembl_id, description, synonyms, length,  transcript_refseq_id ,transcript_ensembl_id
            self.output_db.add_row("Proteins", (n_protein_id, e_protein_id, decription, ";".join(synonyms), length, n_tx_id, e_tx_id))
        return n_protein_id, e_protein_id

    def calculate_abs_coords(self, exons, strand):
        abs_coords = []
        offset = 0
        ordered = exons if strand == '+' else exons[::-1]
        for e in ordered:
            length = e.end - e.start + 1
            abs_coords.append((offset + 1, offset + length))
            offset += length
        return abs_coords if strand == '+' else abs_coords[::-1]

    def get_ensemble_id(self, e_obj):
        if not e_obj:
            return ''   
        version = e_obj.attributes.get('version', [''])[0]
        if version:
            return f"{self.clean_id(e_obj.id)}.{self.clean_id(version)}"
        return self.clean_id(e_obj.id)
   
    def get_dbxref_ensemble_id(self, n_obj):
        if not n_obj:
            return ''   
        dbxrefs = n_obj.attributes.get('Dbxref', [])
        for x in dbxrefs:
            if 'Ensembl' in x:
                return x.split(':')[1]  
        return ''
    
    def add_transcript(self, n_gene_id, e_tx, n_tx):
        e_tx_id = self.get_ensemble_id(e_tx) 
        n_tx_id = self.clean_id(n_tx.id) if n_tx else ''
        #n_gene_id = self.clean_id(n_tx.attributes.get('Parent', [None])[0]) if n_tx else ''
        e_gene_id = self.clean_id(e_tx.attributes.get('Parent', [None])[0]) if e_tx else ''
        transcript = e_tx if e_tx else n_tx
        db = self.e_db if e_tx else self.n_db
        exons = list(db.children(transcript, featuretype='exon', order_by='start'))
        abs_coords = self.calculate_abs_coords(exons, transcript.strand)
        cds_list = list(db.children(transcript, featuretype='CDS', order_by='start'))
        cds_min = min(c.start for c in cds_list) if cds_list else transcript.start
        cds_max = max(c.end for c in cds_list) if cds_list else transcript.end
        offset = (cds_min - transcript.start) if transcript.strand == '+' else (transcript.end - cds_max)
            
        abs_cds_start, abs_cds_stop = self.calculate_cds_boundaries(transcript, cds_list, exons, cds_min, cds_max)
        cds_length = self.calc_transcript_cds_length(db, transcript)
        n_protein_id, e_protein_id = self.add_protein(e_tx, n_tx, cds_length / 3)
        
        if n_tx_id:
            self.transcript_refseq2ensembl[n_tx_id] = e_tx_id   
            self.transcript_map[n_tx_id] = {'offset': offset, 'exons': list(zip(exons, abs_coords))}
        if e_tx_id:
            self.transcript_map[e_tx_id] = {'offset': offset, 'exons': list(zip(exons, abs_coords))}
        self.output_db.add_row("Transcripts",(n_tx_id, e_tx_id, transcript.start, transcript.end, cds_min, cds_max, len(exons), n_gene_id, e_gene_id, n_protein_id, e_protein_id))

        for idx, exon in enumerate(exons):
            self.output_db.add_row("Exons", (n_gene_id, e_gene_id, exon.start, exon.end))
            # transcript_refseq_id, transcript_ensembl_id, order_in_transcript, genomic_start_tx, genomic_end_tx, abs_start_CDS, abs_end_CDS
            self.output_db.add_row("Transcript_Exon", (n_tx_id, e_tx_id, exon.rank, exon.start, exon.end, abs_cds_start[idx], abs_cds_stop[idx]))

    def get_transcript_cds_lengths(self, db, transcript):
        cds_list = list(db.children(transcript, featuretype='CDS', order_by='start'))
        return [abs(c.start - c.end) for c in cds_list] if cds_list else [0]
    
    def match_transcript(self, e_transcripts, n_tx, e_exon_map, e_cds_map, matches):
        n_fingerprint = self.get_exon_fingerprint(self.n_db, n_tx)
        matched_e_tx = e_exon_map.get(n_fingerprint)
        if matched_e_tx:
            return matched_e_tx
        n_cds_length = sum(self.get_transcript_cds_lengths(self.n_db, n_tx)) / 3
        min_diff = float('inf')
        min_tx = None
        for e_tx in e_transcripts:
            if e_tx in matches:
                continue  # Skip already matched Ensembl transcripts
            e_cds_length = sum(e_cds_map.get(self.get_ensemble_id(e_tx), [0])) / 3
            if abs(n_cds_length - e_cds_length) < min_diff:
                min_diff = abs(n_cds_length - e_cds_length)
                min_tx = e_tx
                if min_diff == 0:
                    break  # Perfect match found, no need to continue
        if min_diff <= 1:  # Allow a small difference in CDS length (e.g., due to annotation discrepancies)
            return min_tx
        return None
        # If no exact match, try to find the closest by CDS length
        '''
        n_cds_lengths = self.get_transcript_cds_lengths(self.n_db, n_tx)
        for e_tx in e_transcripts:
            if e_tx in matches:
                continue  # Skip already matched Ensembl transcripts
            e_cds_lengths = e_cds_map.get(self.clean_id(e_tx.id), 0)
            if e_cds_lengths == n_cds_lengths:
                return e_tx
        return None
        '''
    def add_ensembl_protein(self, e_tx, length):
        e_tx_id = self.get_ensemble_id(e_tx) 
        n_tx_id = self.transcripts_e2n.get(e_tx_id, '') 
        e_protein_id = ''
        n_protein_id = ''
        decription = ''
        synonyms = []
        
        e_cds_list = list(self.e_db.children(e_tx, featuretype='CDS', order_by='start'))
        if e_cds_list:
            cds = e_cds_list[0]
            decription = cds.attributes.get('product', [''])[0]
            synonyms.extend(cds.attributes.get('Alias', []))
            e_protein_id = self.get_ensemble_id(e_cds_list[0]) 
            n_protein = self.proteins_e2n.get(e_protein_id, None)  
            if n_protein:
                n_protein_id = n_protein.attributes.get('protein_id', [''])[0]
                decription = n_protein.attributes.get('product', [''])[0]  # Use NCBI description if available
                synonyms.extend(n_protein.attributes.get('Alias', []))  # Add NCBI synonyms if available 
        synonyms = np.unique(synonyms)
        if e_protein_id != '':
            if n_protein_id == '':
                n_protein_id = f"FAKE_{e_protein_id}"
            # protein_refseq_id, protein_ensembl_id, description, synonyms, length,  transcript_refseq_id ,transcript_ensembl_id
            self.output_db.add_row("Proteins", (n_protein_id, e_protein_id, decription, ";".join(synonyms), length, n_tx_id, e_tx_id))
        return n_protein_id, e_protein_id

    def add_ensembl_transcript(self, e_gene, e_tx):
        e_tx_id = self.get_ensemble_id(e_tx) 
        n_tx_id = self.transcripts_e2n.get(e_tx_id, '')
        e_gene_id = self.get_ensemble_id(e_gene)
        n_gene = self.genes_e2n.get(e_gene_id, None) if e_gene_id else None
        n_gene_id = self.refseq_gene_id(n_gene) if n_gene else None
        
        exons = list(self.e_db.children(e_tx, featuretype='exon', order_by='start'))
        if e_gene.strand == '-':
            exons = exons[::-1]
        abs_coords = self.calculate_abs_coords(exons, e_tx.strand)
        cds_list = list(self.e_db.children(e_tx, featuretype='CDS', order_by='start'))
        cds_min = min(c.start for c in cds_list) if cds_list else e_tx.start
        cds_max = max(c.end for c in cds_list) if cds_list else e_tx.end
        offset = (cds_min - e_tx.start) if e_tx.strand == '+' else (e_tx.end - cds_max)

        cds_length = self.calc_transcript_cds_length(self.e_db, e_tx)    
        abs_cds_start, abs_cds_stop= self.calculate_cds_boundaries(e_tx, cds_list, exons, cds_min, cds_max)
        n_protein_id, e_protein_id = self.add_ensembl_protein(e_tx, (cds_length / 3) - 1)  # Subtract 1 to account for stop codon
        
        self.transcript_map[e_tx_id] = {'offset': offset, 'exons': list(zip(exons, abs_coords))}
        if len(n_tx_id) == 0:
            n_tx_id = f"FAKE-{e_tx_id}"  # Create a synthetic NCBI ID for unmatched Ensembl transcripts
        self.output_db.add_row("Transcripts",(n_tx_id, e_tx_id, e_tx.start, e_tx.end, cds_min, cds_max, len(exons), n_gene_id, e_gene_id, n_protein_id, e_protein_id))

        cds_offset = 1
        for idx, exon in enumerate(exons):
            self.output_db.add_row("Exons", (n_gene_id, e_gene_id, exon.start, exon.end))
            rank = exon.attributes.get('rank', [0])[0]  # Use exon rank
            cur_cds_start = max(exon.start, cds_min)
            cur_cds_end = min(exon.end, cds_max)
            cds_len = abs(cur_cds_end - cur_cds_start) + 1
            if cur_cds_start > cur_cds_end:
                self.output_db.add_row("Transcript_Exon", (n_tx_id, e_tx_id, rank, exon.start, exon.end, 0, 0))
            else:
                self.output_db.add_row("Transcript_Exon", (n_tx_id, e_tx_id, rank, exon.start, exon.end, cds_offset, cds_offset + cds_len - 1))
                cds_offset += cds_len

    def add_ensembl_transcripts(self, e_gene):
        for e_tx in self.e_db.children(e_gene.id, featuretype=['transcript', 'mRNA']):
            if self.is_protein_coding(self.e_db, e_tx):
                self.add_ensembl_transcript(e_gene, e_tx)

    def add_transcripts(self, n_gene_id, n_gene, e_gene):
        matches = {} # Maps Ensembl transcript IDs to matched NCBI transcript objects
        e_transcripts =[] # list of all protein-coding transcripts for this Ensembl gene
        e_map = {} # map ensembl full_id to transcript object for quick lookup during matching
        e_cds_map = {} # Maps Ensembl transcript IDs to their CDS lengths for tie-breaking
        if e_gene:
            for e_tx in self.e_db.children(e_gene.id, featuretype=['transcript', 'mRNA']):
                if self.is_protein_coding(self.e_db, e_tx):
                    e_transcripts.append(e_tx)
                    full_id = self.get_ensemble_id(e_tx)
                    e_map[full_id] = e_tx
                    e_cds_map[full_id] = self.get_transcript_cds_lengths(self.e_db, e_tx)
        if n_gene:    
            for n_tx in self.n_db.children(n_gene, featuretype=['transcript', 'mRNA']):
                if not self.is_protein_coding(self.n_db, n_tx):
                    continue  
                e_tx_id = self.get_dbxref_ensemble_id(n_tx)
                matched_e_tx = e_map.get(e_tx_id, None) # First try direct ID match
                if not matched_e_tx:
                    matched_e_tx = self.match_transcript(e_transcripts, n_tx, e_map, e_cds_map, matches)
                if matched_e_tx:
                    logger.debug(f"NCBI transcript match found for  {n_tx.id} with Ensembl transcript {e_tx_id}")
                    matches[matched_e_tx] = n_tx
                else:           
                    logger.debug(f"NCBI transcript no match found for  {n_tx.id})")
                self.add_transcript(n_gene_id, matched_e_tx, n_tx)
        for e_tx in e_transcripts:
            if e_tx not in matches:
                logger.debug(f"Ensembl transcript no match found for  {self.get_ensemble_id(e_tx)}.")
                self.add_transcript(n_gene_id, e_tx, None)

    def is_primary_chromosome(self, db, seqid):
        """
        A universal check for primary vs alternative sequences.
        """
        # 1. Accession check (Works for almost all RefSeq species)
        if seqid.startswith('NC_'):
            return True

        # 2. Attribute check (The safety net for Ensembl and others)
        try:
            region = db[seqid]
        except gffutils.exceptions.FeatureNotFoundError:
            region = None
        if not region:
            return True
        attr_string = str(region.attributes).lower()

        # Keywords that indicate it's NOT a primary chromosome
        alt_keywords = ['unplaced', 'scaffold', 'alt-loci', 'patch', 'contig', 'unlocalized']

        if any(word in attr_string for word in alt_keywords):
            return False
            
        # Keywords that indicate it IS a primary chromosome
        if 'chromosome' in attr_string or 'linkage-group' in attr_string:
            return True
        return False

    def track_progress(self, counter, last_print_time,msg):
        counter += 1
        current_time = time.time()
        if counter % 1000 == 0 or (current_time - last_print_time >= self.print_interval):
            self.output_db.flush_buffers(force=False)
            logger.info(msg + str(counter))
        last_print_time = current_time
        return counter, last_print_time
    
    def extract_cdd_accession_from_note(self, note: str) -> str | None:
        """Try to find a CDD accession like cd05711 or PRK12345 in the /note text."""
        match = re.search(r'\b(cd\d{5}|PRK\d+|pfam\d+|smart\d+|TIGR\d+)\b', note, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def get_record_ensemble_tran_prot(self, rec: SeqIO.SeqRecord) -> Tuple[Optional[str], Optional[str]]:
        """Extracts ENST and ENSP IDs from a SeqRecord's structured comments."""
        if mane := rec.annotations.get('structured_comment', {}).get('RefSeq-Attributes', {}).get('MANE Ensembl match'):
            return tuple(part.strip() for part in mane.split('/'))
        return None, None

    def parse_cdd_xref(self, xrefs) -> tuple[str | None, str | None]:
        """Return (cdd_label, cdd_numeric_id) from a list of db_xref strings.
        e.g. 'CDD:409376' -> ('409376', 'cd05711' would come from /note)
        """
        for xref in xrefs:
            if xref.startswith("CDD:"):
                return xref.split(":", 1)[1], None
        return None, None

    def process_refseq_protein_gpff_files(self):
            logger.info(f"  Processing RefSeq GPFF for proteins and domains")
            cdd_map, accession_map = self.parse_interpro_domain_map(self.interpro_domain_file)
            cdd_idd_type_id_map = {} # Map between CDD numeric ID (e.g. 409376) to domain_type_id
            accession_type_id_map = {} # Map between CDD accessions (e.g. cd05711) to domain_type_id
            self.output_db.connect()
            self.domain_types_counter = 0
            for f in self.ncbi_gpff_files:
                logger.info(f"Processing GPFF file: {f}")
                self.process_single_protein_gpff_file(f, cdd_map, accession_map, cdd_idd_type_id_map, accession_type_id_map)

    def parse_interpro_domain_map(self, file_path: Path) -> tuple[dict[int, dict], dict[str, dict]]:
        """Returns cache keyed by both lowercase accession AND numeric PSSM-Id string.
        Both keys point to the same dict object so enrichment via either key is reflected.
        """
        logger.info(f"Parsing InterPro domain map from {file_path}...")
        cdd_cache: dict[int, dict] = {}
        acc_cache: dict[str, dict] = {}

        with gzip.open(file_path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue
                pssm_id, accession, short_name, description = parts[:4]
                cdd, pfam,smart,tigr,interpro = None, None,None,None,None
                acc_key = accession.lower()
                if acc_key.startswith("pfam") or acc_key.startswith("pf"):
                    pfam = accession
                elif acc_key.startswith("smart") or acc_key.startswith("sm"):
                    smart = accession
                elif acc_key.startswith("tigrt") or acc_key.startswith("ncbifam"):
                    tigr = accession
                elif acc_key.startswith("cd"):
                    cdd = accession

                record = {
                    "cdd_id":      pssm_id,
                    "name":        short_name.strip() or None,
                    "other_name":  None,
                    "description": description.strip() or None,
                    "cdd":         cdd,
                    "pfam":        pfam,
                    "smart":       smart,
                    "tigr":        tigr,
                    "interpro":    None,
                }
                num_key = int(pssm_id.strip())
                if acc_key:
                    acc_cache[acc_key] = record
                if num_key:
                    cdd_cache[num_key] = record  # same object — enrichment writes once, visible via both keys
        return cdd_cache, acc_cache

    def process_single_protein_gpff_file(self, f, cdd_map, accession_map, cdd_idd_type_id_map, accession_type_id_map):           
        time_start = time.time()
        last_print_time = time_start
        counter = 0
        with gzip.open(f, "rt") as handle:  # "rt" stands for Read Text mode
            for record in SeqIO.parse(handle, "genbank"):
                msg = "\tStatus Update: Processed records:"
                counter, last_print_time = self.track_progress(counter, last_print_time, msg)
                # get protein-level information (ID, length, description, synonyms, corresponding transcript ID)
                protein_id = self.clean_id(record.id)
                protein_len = len(record.seq)
                protein_feature = [p for p in record.features if p.type == 'Protein'][0]
                protein_synonyms = protein_feature.qualifiers.get('product', [''])[0] or protein_feature.qualifiers.get('note', [''])[0]
                cds_feature = [p for p in record.features if p.type == 'CDS'][0]
                t_id = self.clean_id(cds_feature.qualifiers.get("coded_by", [""])[0].split(":")[0]) ## find the corresponding transcript ID 
                if t_id not in self.transcript_map:
                    logger.warning(f"Transcript ID {t_id} for protein {protein_id} not found in transcript map. Skipping protein.")
                    continue
                ensembl_transcript_id, ensembl_protein_id = self.get_record_ensemble_tran_prot(record)
                self.output_db.add_row("Proteins", (protein_id, ensembl_protein_id, record.description, protein_synonyms, protein_len, t_id, ensembl_transcript_id))
                
                # find region/domain features and extract CDD annotations
                for feature in record.features:
                    if feature.type != "Region":
                        continue
                    qualifiers = feature.qualifiers
                    region_name = qualifiers.get("region_name", [None])[0]
                    note = qualifiers.get("note", [""])[0]
                    # We only care about CDD-annotated regions
                    cdd_id, cdd_accession = self.parse_cdd_xref(qualifiers.get("db_xref", []))
                    # Try to extract a named CDD accession from /note
                    if not cdd_accession:
                        cdd_accession = self.extract_cdd_accession_from_note(note)
                    if not cdd_id and not cdd_accession:
                        logger.warning(f"Record {protein_id} has a Region {region_name} without a CDD/accession annotation. Skipping.")
                        continue
                    if cdd_id in cdd_idd_type_id_map or (cdd_accession and cdd_accession in accession_type_id_map):
                        continue
                    self.domain_type_counter += 1
                    cdd_idd_type_id_map[cdd_id] = self.domain_type_counter
                    if cdd_accession:
                        accession_type_id_map[cdd_accession] = self.domain_type_counter    
                    description = note[0] if note else None
                    aa_start = int(feature.location.start) + 1  # 1-based
                    aa_end = int(feature.location.end)
            
                    pfam_val, smart_val, interpro_val, ensembl_val, other_name = None, None, None, None, None
                    cdd_info =  cdd_map.get(cdd_id, None) or accession_map.get(cdd_accession, None)
                    if cdd_info:
                        pfam_val = cdd_info.get('Pfam')
                        smart_val = cdd_info.get('SMART')
                        interpro_val = cdd_info.get('InterPro')
                        other_name = cdd_info.get('other_name', '')
                    # Insert all 10 columns: type_id, name, other_name, description, CDD_id, cdd, pfam, smart, tigr, interpro
                    self.output_db.add_row("DomainType", (self.domain_type_counter, region_name, other_name, description, cdd_id, cdd_accession, pfam_val, smart_val, None, interpro_val))
                    aa_s, aa_e = int(feature.location.start), int(feature.location.end)
                    is_splice = self.handle_splice_domains(t_id, protein_id, ensembl_protein_id, region_name, aa_s, aa_e)
                    self.output_db.add_row("DomainEvent", (protein_id, ensembl_val, self.domain_type_counter, aa_s, aa_e, aa_s*3, aa_e*3, (aa_e-aa_s)*3, "", is_splice, 1))
        self.output_db.flush_buffers(force=True)
        self.output_db.commit()
        logger.info(f"  Finished processing GPFF file: {f}. Total records: {counter}. Time elapsed: {time.time() - time_start:.2f} seconds")

    def handle_splice_domains(self, t_id, refseq_protein_id, ensemble_protein_id, region_name, aa_s, aa_e):
        if t_id not in self.transcript_map: return 0
        info = self.transcript_map[t_id]
        d_nuc_s, d_nuc_e = (aa_s * 3) + info['offset'], (aa_e * 3) + info['offset']
        hit_exons = []
        for i, (exon_feat, (abs_s, abs_e)) in enumerate(info['exons']):
            overlap_s, overlap_e = max(d_nuc_s, abs_s), min(d_nuc_e, abs_e)
            if overlap_s < overlap_e:
                hit_exons.append(i + 1)
                domain_type_id = self.domain_type_map.get(region_name, None)
                self.output_db.add_row("SpliceInDomains", (refseq_protein_id, ensemble_protein_id, i+1, overlap_s, domain_type_id, d_nuc_e-d_nuc_s, overlap_e-overlap_s, len(hit_exons)))
        return 1 if len(hit_exons) > 1 else 0

    def process_ensembl_domains(self, sp_dir, sp_name):
        logger.info(f"  Processing Ensembl domain annotations for {sp_name}...")
        external_dbs = ["interpro", "pfam", "smart", "tigrfams"]
        self.output_db.connect()
        time_start = time.time()
        last_print_time = time_start
        for ext in external_dbs:
            logger.info(f"    Checking for {ext} domain file...")
            f_path = os.path.join(sp_dir, "ensembl", f"{sp_name}.Domains.{ext}.txt")
            if not os.path.exists(f_path): 
                continue
            try: 
                df = pd.read_table(f_path, sep="\t")
            except Exception as e:
                logger.warning(f"    Could not read {f_path} due to error: {e}. Skipping.")
                continue
            df.columns = ['protein_stable_id', 'transcript_stable_id', 'domain_id', 'start', 'end', 'description']
            df.dropna(subset=['protein_stable_id', 'domain_id', 'start', 'end'], inplace=True)
        
            for counter, row in df.itertuples():
                if counter % 1000 == 0:
                    self.output_db.flush_buffers(force=False)
                current_time = time.time()
                if current_time - last_print_time >= self.print_interval:
                    logger.info(f"\tStatus Update: Processed {counter} {ext} records. Time: {time.ctime()}")
                    last_print_time = current_time
                p_id = self.clean_id(row.protein_stable_id) 
                t_id = self.clean_id(row.transcript_stable_id)
                reg_name = row.domain_id
                regID = hash(reg_name)
                if regID not in self.domain_type_map:
                    # Insert all 10 columns, populate the appropriate source column
                    pfam_val = reg_name if ext == 'pfam' else None
                    smart_val = reg_name if ext == 'smart' else None
                    tigr_val = reg_name if ext == 'tigrfams' else None
                    interpro_val = reg_name if ext == 'interpro' else None
                    self.domain_type_counter += 1
                    self.output_db.add_row("DomainType", (self.domain_type_counter, reg_name, None, row.description, None, None, pfam_val, smart_val, tigr_val, interpro_val))
                    self.domain_type_map[regID] = self.domain_type_counter
                    
                aa_s, aa_e = int(row.start), int(row.end)
                is_splice = self.handle_splice_domains(t_id, None, p_id, regID, aa_s, aa_e)
                domain_type_id = self.domain_type_map[regID]
                self.output_db.add_row("DomainEvent", (None, p_id, domain_type_id, aa_s, aa_e, aa_s*3, aa_e*3, (aa_e-aa_s)*3, row.id, is_splice, 1))
            logger.info(f"    Finished processing {ext} domains. Total records: {counter}. Time elapsed: {time.time() - time_start:.2f} seconds")
            self.output_db.flush_buffers(force=True)
            self.output_db.commit()


    # --- PASS 3: Multi-Species Orthology ---
    def process_multi_species_orthology(self, file_path, source_species, gene_symbol_cache):
        if not os.path.exists(file_path): return
        logger.info(f"  Parsing orthology file: {file_path}")
        time_start = time.time()
        last_print_time = time_start
        df = pd.read_table(file_path, sep="\t")
        source_col = df.columns[0]

        # Map species from column names to database species names
        species_mapping = {
            "Human": "H_sapiens",
            'Mouse': 'M_musculus',
            'Norway rat': 'R_norvegicus',
            'Zebrafish': 'D_rerio',
            'Tropical clawed frog': 'X_tropicalis'
        }

        self.output_db.connect()
        self.output_db.cur.execute("BEGIN TRANSACTION;")
        total_pairs = 0
        for i in range(1, len(df.columns), 2):
            target_id_col = df.columns[i]
            type_col = df.columns[i+1]
            
            # Extract target species from column name
            target_species = None
            for species_key, species_value in species_mapping.items():
                if species_key in target_id_col:
                    target_species = species_value
                    break
            
            if not target_species:
                logger.warning(f"    Could not determine species for column '{target_id_col}'. Skipping.")
                continue
            
            # dropna handles the lack of filters in the wget query
            subset = df[[source_col, target_id_col]].dropna()
            for _, row in subset.iterrows():
                total_pairs += 1
                if total_pairs % 10000 == 0:
                    self.output_db.flush_buffers(specific_table="Orthology", force=False)
                current_time = time.time()
                if current_time - last_print_time >= self.print_interval:
                    logger.info(f"\tStatus Update: Processed {total_pairs} orthology pairs. Time: {time.ctime()}")
                    last_print_time = current_time
                
                source_id = self.clean_id(row[0])
                target_id = self.clean_id(row[1])
                source_symbol = gene_symbol_cache.get(source_id, "")
                target_symbol = gene_symbol_cache.get(target_id, "")
                self.output_db.add_row("Orthology", (source_id, source_symbol, source_species, target_id, target_symbol, target_species))
            self.output_db.flush_buffers(specific_table="Orthology", force=True)
            self.output_db.commit()
            logger.info(f"  Finished processing orthology file. Total orthology pairs: {total_pairs}. Time elapsed: {time.time() - time_start:.2f} seconds")

def find_file(input_path, patterns):
    input_path = Path(input_path)
    for p in patterns:
        files = list(input_path.glob(p))
        if files:
            return files[0]
    raise FileNotFoundError(f'File not found. path: {input_path}, patterns: {patterns}')
    
def run_merger(input_path, specie, db_out):
    """Find GFF and GPFF files by their postfix patterns and create database."""
    # Find files matching the patterns
    input_path = Path(input_path)
    ncbi_input_path = input_path / specie / "refseq"
    ensembl_input_path = input_path / specie / "ensembl"
    ncbi_gff = find_file(ncbi_input_path, ["*_genomic.gff", "*_genomic.gff.gz"])
    ncbi_gpff_pattern = ncbi_input_path / "*.*.protein.gpff.gz"
    ensembl_gff = find_file(ensembl_input_path, [ "*.gff3", "*.gff3.gz"])
    interpro_domain_file = input_path / specie / "interpro.xml.gz"
    
    logger.info(f"Found NCBI GFF: {ncbi_gff}")
    logger.info(f"Found Ensembl GFF: {ensembl_gff}")
    logger.info(f"NCBI GPFF pattern: {ncbi_gpff_pattern}")
    logger.info(f"InterPro domain file: {interpro_domain_file}")
    merger = DoChaPCMerger(ncbi_gff=ncbi_gff, 
                           ensembl_gff=ensembl_gff, 
                           species=specie, 
                           ncbi_gpff_pattern=ncbi_gpff_pattern, 
                           interpro_domain_file=interpro_domain_file, 
                           db_out=db_out)
    merger.create_db()
    #merger.traverse_ensembl()
    #merger.process_refseq_protein_gpff_files()
    #results = [f for f in merger.e_db.features_of_type('gene') if 'CUTA' in f.attributes.get('Name', [])]
    #e_gene = results[0] if results else None
    #results = [f for f in merger.n_db.features_of_type('gene') if 'CUTA' in f.attributes.get('Name', [])]
    #n_gene = results[0] if results else None
    #n_gene_id = merger.clean_id(n_gene.seqid) if n_gene else ''
    #merger.add_transcripts(n_gene_id, n_gene, e_gene)
def main():
    run_merger("/gpfs0/tals/projects/Analysis/ariel/DoChap/DoChaP-db/try1/genomic_data/", "H_sapiens", "unified_genome.db")
    if len(sys.argv) != 4:
        print("Usage: python gemini_download.py <input_path> <species> <output_db>")
        print("Example: python gemini_download.py /data/genomes H_sapiens unified_genome.db")
        sys.exit(1)
    
    input_path = sys.argv[1]
    species = sys.argv[2]
    output_db = sys.argv[3]
    
    run_merger(input_path, species, output_db)
    
if __name__ == "__main__":
    main()
