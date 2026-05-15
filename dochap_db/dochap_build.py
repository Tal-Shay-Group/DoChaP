import json
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
from pyparsing import col
from pathlib import Path
import xml.etree.ElementTree as ET 


# Add current script directory to path to ensure local imports
script_dir = Path(__file__).parent.absolute()
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from dochap_db import DoChaPDB
from dochap_download_doamins import query_domains, create_domain_types
import dochap_parse_protein_gpff
# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class DoChaPCBuilder:
    def __init__(self, ncbi_gff, ensembl_gff, species, 
                 ncbi_gpff_pattern, interpro_domain_file, cddid_file, 
                 db_out, print_interval=60):
        logger
        # Initialize gffutils databases (in-memory for speed if files aren't massive)
        self.domain_type_map = {}  # Map between reg hash to id
        self.transcript_map = {} # {t_id: {'offset': int, 'exons': [(abs_s, abs_e, idx)]}}
        self.transcript_refseq2ensembl = {} # {refseq_tx_id: ensembl_tx_id}
        self.genes_e2n = {}
        self.transcripts_e2n = {}
        self.cds_e2n = {}
        self.protein_n2e = {}
        self.print_interval = print_interval
        self.species = species
        self.domain_type_counter = 0
        self.domains = dict()  # region name -> type_id
        self.my_domains = {}  # interpro_acc -> values
        
        self.interpro_domain_file = interpro_domain_file
        self.cddid_file = cddid_file
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

    def refseq_gene_id(self, n_gene):
        dbxrefs = n_gene.attributes.get('Dbxref', [])
        return next((x.split(':')[1] for x in dbxrefs if 'GeneID' in x), '')
        
    def map_genes_transcripts_proteins(self):
        '''
        if os.path.exists(f'mapping_summary_{self.species}.json'):
            data = json.load(open(f'mapping_summary_{self.species}.json'))
            self.genes_e2n = {k: None for k in range(data['Mapped Genes'])}
            self.transcripts_e2n = {k: None for k in range(data['Mapped Transcripts'])}
            self.cds_e2n = {k: None for k in range(data['Mapped Proteins'])}
            logger.info(f"Loaded existing mapping summary for {self.species}, skipping mapping step.")
            return
        '''
        e_db_index = self.build_gene_name_index(self.e_db)  # Build an index for quick name-based lookups in Ensembl
        
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
        for n_cds in self.n_db.features_of_type('CDS'):
            counter , last_print_time = self.track_progress(counter, last_print_time, msg)
            n_protein_id = n_cds.attributes.get('protein_id', [''])[0]
            ensembl_id = self.get_dbxref_ensemble_id(n_cds)  
            if ensembl_id:
                self.cds_e2n[ensembl_id] = n_cds
                self.protein_n2e[n_protein_id] = ensembl_id
        data = {    
            'Mapped Genes': len(self.genes_e2n),    
            'Mapped Transcripts': len(self.transcripts_e2n),
            'Mapped Proteins': len(self.cds_e2n)
        }
        json.dump(data, open(f'mapping_summary_{self.species}.json', 'w'), indent=4)
        

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
            self.add_ensembl_transcripts(e_gene, n_gene) 
        self.output_db.flush_buffers(force=True) 

                

    def create_db(self):
        self.traverse_ensembl()
        self.output_db.flush_buffers(force=True)
        self.output_db.commit()

        self.process_refseq_protein_gpff_files()
        self.output_db.flush_buffers(force=True)
        self.output_db.commit()
        self.output_db.create_index()
        self.output_db.commit()
        self.output_db.close()
                
        logger.info(f"Merging {self.species} complete.")
        

    def is_protein_coding(self, db, transcript):
        biotype = transcript.attributes.get('biotype', [])
        if biotype and 'protein_coding' not in biotype:
            return False
        cds_count = len(list(db.children(transcript, featuretype='CDS')))
        return cds_count > 0

    def calc_transcript_cds_length(self, db, transcript):
        cds_list = list(db.children(transcript, featuretype='CDS'))
        length = sum(abs(c.start - c.end) + 1 for c in cds_list)
        return length

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
    
    def ncbi_get_parent_id(self, n_obj):
        if not n_obj:
            return ''
        parent_id = n_obj.attributes.get('Parent', [''])[0]
        version_num = n_obj.attributes.get('version', [''])[0]
        if parent_id and version_num and not '.' in parent_id:
            parent_id += '.' + version_num
        return self.clean_id(parent_id)
    
    def add_ensembl_protein(self, e_tx, length):
        e_tx_id = self.get_ensemble_id(e_tx) 
        n_tx_id = self.transcripts_e2n.get(e_tx_id, '') 
        e_protein_id = None
        n_protein_id = None
        decription = ''
        synonyms = []
        
        e_cds_list = list(self.e_db.children(e_tx, featuretype='CDS', order_by='start'))
        if e_cds_list:
            cds = e_cds_list[0]
            decription = cds.attributes.get('product', [''])[0]
            synonyms.extend(cds.attributes.get('Alias', []))
            e_protein_id = self.get_ensemble_id(cds) 
            n_cds = self.cds_e2n.get(e_protein_id, None)  
            if n_cds:
                n_protein_id = n_cds.attributes.get('protein_id', [None])[0]
                if not n_tx_id:
                    n_tx_id = self.ncbi_get_parent_id(n_cds) 
                decription = n_cds.attributes.get('product', [None])[0]  # Use NCBI description if available
                synonyms.extend(n_cds.attributes.get('Alias', []))  # Add NCBI synonyms if available 
        synonyms = np.unique(synonyms)
        if e_protein_id:
            if n_protein_id is None:
                n_cds = self.cds_e2n.get(e_protein_id, None)
                if n_cds: 
                    n_protein_id = n_cds.attributes.get('protein_id', [None])[0] if n_cds else None
            # protein_refseq_id, protein_ensembl_id, description, synonyms, length,  transcript_refseq_id ,transcript_ensembl_id
            self.output_db.add_row("Proteins", (n_protein_id, e_protein_id, decription, ";".join(synonyms), length, n_tx_id, e_tx_id))
        return n_protein_id, e_protein_id

    def add_ensembl_transcript(self, e_gene, n_gene, e_tx, n_tx_id):
        e_tx_id = self.get_ensemble_id(e_tx) 
        e_gene_id = self.get_ensemble_id(e_gene)
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
        n_protein_id, e_protein_id = self.add_ensembl_protein(e_tx, (cds_length / 3) - 1)  # Subtract 1 to account for stop codon
        
        self.transcript_map[e_tx_id] = {'offset': offset, 'exons': list(zip(exons, abs_coords))}
        if not n_tx_id:
            n_tx_id = None
        else:
            self.transcript_refseq2ensembl[n_tx_id] = e_tx_id
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
        self.add_ensembl_domains(e_tx, n_tx_id, e_protein_id, n_protein_id)

    def add_ensembl_domains(self, e_tx, n_tx_id, e_protein_id, n_protein_id):
        pass

    def add_ensembl_transcripts(self, e_gene, n_gene):
        # first match by transcript dbxref, than by cds's transcript than by cds length
        matches= {}
        n_matched_ids = set()
        n_transcripts_lengths = []
        # gather NCBI transcript CDS lengths for tie-breaking if needed
        if n_gene:
            for n_tx in self.n_db.children(n_gene, featuretype=['transcript', 'mRNA']):
                if not self.is_protein_coding(self.n_db, n_tx):
                    continue
                cds_list = list(self.n_db.children(n_tx, featuretype='CDS', order_by='start'))
                cds_length = sum(abs(c.start - c.end) for c in cds_list) if cds_list else 0
                n_transcripts_lengths.append((n_tx, cds_length))
        # match Ensembl transcripts to NCBI transcripts using multiple strategies
        for e_tx in self.e_db.children(e_gene.id, featuretype=['transcript', 'mRNA']):
            if not self.is_protein_coding(self.e_db, e_tx):
                continue
            # match by transcript dbxref first
            n_tx_id = self.transcripts_e2n.get(self.get_ensemble_id(e_tx), None)
            if not n_tx_id:  # if no match by dbxref, try to match by CDS's transcript
                cds_list = list(self.e_db.children(e_tx, featuretype='CDS', order_by='start'))
                if cds_list:
                    n_cds = self.cds_e2n.get(self.get_ensemble_id(cds_list[0]), None)
                    n_tx_id = self.ncbi_get_parent_id(n_cds) if n_cds else None
            if not n_tx_id: # if still no match, try to match by CDS length
                e_cds_length = sum(abs(c.start - c.end) for c in cds_list)
                for n_tx, n_cds_length in n_transcripts_lengths:
                    if not self.clean_id(n_tx.id) in n_matched_ids:  
                        if e_cds_length == n_cds_length:  
                            n_tx_id = self.clean_id(n_tx.id)
                            break  
            if n_tx_id:
                matches[e_tx] = n_tx_id
                n_matched_ids.add(n_tx_id)    
            self.add_ensembl_transcript(e_gene, n_gene, e_tx, n_tx_id)
            

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
        con = sqlite3.connect('/gpfs0/tals/projects/Analysis/ariel/DoChap/dochap_db/genomic_data/protein_domains.sqlite')  # TBD
        df_domain_types, df_interpro_domain_type_id = create_domain_types(con)
        for row in df_domain_types.itertuples():
            self.output_db.add_row("DomainType", (row.type_id, row.name, row.other_name, 
                                                  row.description, row.CDD_id, row.cdd, 
                                                  row.pfam, row.smart, row.tigr, row.interpro))
        self.output_db.flush_buffers(force=True)
        for f in self.ncbi_gpff_files:
            logger.info(f"Processing GPFF file: {f}")
            self.process_single_protein_gpff_file(f, con, df_domain_types, df_interpro_domain_type_id)
        con.close()


    def process_refseq_protein_gpff_files2(self):
            '''
            DomainType table: domain_type_id, name, other_name, description, cdd_id, cdd_accession, pfam, smart, tigr, interpro
            1) read cddid.tbl.gz: ccd_id, accession, short_name, description, length
            2) read interpro.xml.gz:  ccd_id, name, description, 
               member dbs (pfam, smart, tigr, cdd, interpro_id, profile), short_name
            3) if cdd_id is present in 1, complete the data from 2.
               if not add the record with whatever info is available from 1 and enrich if possible when we read 2.
            4) Read refseq protein GPFF filea, match CDS using cdd_id or cdd_accession in the /note,
                extract the corresponding transcript ID, match to ensembl transcript ID if possible
            DomainEvent table: protein_refseq_id, protein_ensembl_id, domain_type_id, aa_start, aa_end, cds_start, cds_end, length, description, is_splice, evidence_level
            5) Go over all CDS features in the refseq GPFF, if they have a Region feature with cdd annotation, 
               Create a DomainEvent entry with the corresponding domain_type_id and coordinates and transcript ID. 
            6) for ensembl, we dont have direct domain annotations, but we can lift over the domain coordinates from refseq to ensembl using the transcript exon structures and create DomainEvent entries with null domain_type_id but with description indicating it's lifted over from refseq.   
               
            '''
            logger.info(f"  Processing RefSeq GPFF for proteins and domains")
            df_domain_types, accession_prefixes = self.prepare_domain_type()  
            df_domain_types['counter'] = 0
            self.domain_types_counter = 0
            for f in self.ncbi_gpff_files:
                logger.info(f"Processing GPFF file: {f}")
                self.process_single_protein_gpff_file2(f, df_domain_types, accession_prefixes)

    def add_column_as_int(self, df, column_name, dest_col_name):
        # Removes all leading/trailing non-digit characters  and converts the column to a numeric integer type.

        # 1. Extract only the digits (\d+) from the string
        # This turns "cd12345" into "12345" and "pfam00789" into "00789"
        df[dest_col_name] = df[column_name].astype(str).str.extract(r'(\d+)')
        
        # 2. Convert to numeric (errors='coerce' turns empty/invalid matches to NaN)
        df[dest_col_name] = pd.to_numeric(df[dest_col_name], errors='coerce')
        
        # 3. Fill NaNs with 0 (optional) and cast to Int64 
        # (Int64 with capital 'I' handles NaNs better than standard int)
        df[dest_col_name] = df[dest_col_name].fillna(0).astype(int)
        return df

    # return True if found the accession
    # if the prefix matches, tries to update pssm_id if the numeric part match given columns
    def match_accession(self, df_interpro, cddid_row, prefixes_map):
        accession = cddid_row.accession.lower()
        column_name = prefixes_map.get(accession[:2], None) # match first 2 characters 
        accession_id = int(''.join(filter(str.isdigit, accession))) 
        matches = df_interpro.index[df_interpro[column_name + "_id"]  == accession_id]
        if len(matches):
            df_interpro.at[matches[0], 'pssm_id'] = int(cddid_row.pssm_id)
            return True
        return False
        
        
    def prepare_domain_type(self):
        accession_prefixes = {'cd' : 'cdd', 'sm': 'smart', 'pf': 'pfam', 'tigr': 'tigr', 'ipr': 'interpro', 'ps': 'profile',
                              'nf' : 'NCBIfam', 'pr': 'PRK', 'pl': 'PLN'} # supported accession prefixes and their corresponding column names in interpro df
        accession_columns = list(accession_prefixes.values())
        df_cddid = pd.read_csv(self.cddid_file, sep="\t", header=None, names=["pssm_id", "accession", "name", "description", "length"]).astype(str)
        df_interpro = self.parse_interpro_domain_map().astype(str)
        # try to match the accession from cddid to one of interpro accessions (cdd, pfam, smart, tigr) 
        # if matched update pssm_id
        df_interpro['pssm_id'] = 0
        # add a culumn per db that holds the numeric part of the accession to make matching easier.
        df_interpro[accession_columns] = df_interpro[accession_columns].apply(lambda x: x.str.lower())
        # add int id column per each accession type to make matching easier (e.g. cd05711 -> 5711, pfam00789 -> 789)
        for col in accession_columns:
            df_interpro = self.add_column_as_int(df_interpro, col, f"{col}_id")
        for idx, row in df_cddid.iterrows():
            if not accession_prefixes.get(row.accession[:2], None):
                continue # not a supported accession prefix, skip
            if self.match_accession(df_interpro, row, accession_prefixes):
                continue # matched to interpro, pssm_id updated, skip to next row   
            accession = row.accession.lower()
            column_name = accession_prefixes.get(accession[:2], None) # match first 2 characters 
            if column_name is not None:
                colunm_id = column_name + '_id'
                new_row = {'pssm_id': row['pssm_id'], 'name': row['name'], 'description': row['description'], 
                            column_name: row['accession'], colunm_id: int(''.join(filter(str.isdigit, row.accession)))}
                df_interpro = pd.concat([df_interpro, pd.DataFrame([new_row])], ignore_index=True)
        df_interpro['counter'] = 0 # domain type counter
        return df_interpro, accession_prefixes      
        
    def parse_interpro_domain_map(self) -> pd.DataFrame:
        records = []
        with gzip.open(self.interpro_domain_file, "rt", encoding="utf-8", errors="replace") as fh:
            tree = ET.parse(fh)
            root = tree.getroot()
            intros = root.findall("interpro")
            for intr in intros:
                if intr.attrib.get('type', '') != 'Domain':  
                    continue
                pfam, cdd, smart, tigr, profile = None, None, None, None, None
                intrpro_id = intr.attrib.get('id', '')
                name = intr.find('name').text
                short_name = intr.attrib.get('short_name', None)
                if name and short_name: 
                    name = short_name if len(short_name) < len(name) else name
                abstract_element = intr.find('.//abstract/p')
                description = "".join(abstract_element.itertext()).strip() if abstract_element is not None else ''
                # other_names holds all accessions from different dbs (cdd, pfam, smart, tigr) as well as interpro id 
                # the prefix must be according to GUI requirements (e.g. pfam accessions must start with 'pfam' followed by the numeric part) 
                other_names = set()  # 
                dbs = intr.findall("member_list/db_xref")
                for db in dbs:
                    if db.attrib.get('db', '') in ['PFAM', 'SMART', 'TIGRFAM', 'CDD', 'PROFILE']:
                        if db.attrib.get('db', '') == 'PFAM':
                            pfam = db.attrib.get('dbkey', '')
                            pfam = 'pfam' + str(self.remove_non_numeric_prefix(pfam)) # check if pfam accession has numeric part, if not set pfam to None to avoid matching it to cdd accessions that also start with 'pf'
                        elif db.attrib.get('db', '') == 'SMART':
                            smart = db.attrib.get('dbkey', '')
                            smart = 'smart' + str(self.remove_non_numeric_prefix(smart)) 
                        elif db.attrib.get('db', '') == 'TIGRFAM':
                            tigr = db.attrib.get('dbkey', '')
                            tigr = 'TIGR' + str(self.remove_non_numeric_prefix(tigr))
                        elif db.attrib.get('db', '') == 'CDD':
                            cdd = db.attrib.get('dbkey', '')
                            cdd = 'cd' + str(self.remove_non_numeric_prefix(cdd))
                        #elif db.attrib.get('db', '') == 'PROFILE': TBD not supported by GUI
                        #    profile = db.attrib.get('dbkey', '')
                other_names.update([pfam, smart, tigr, cdd, intrpro_id])
                other_names.discard(None)
                other_names = ";".join(list(other_names))
                records.append((cdd, name ,other_names, description, pfam, smart, tigr, intrpro_id, profile))
        df = pd.DataFrame(records, columns=["cdd", "name" , "other_name", "description", "pfam", "smart", "tigr", "interpro", "profile"])
        return df

    def get_numeric(self, accession):
        return int(''.join(filter(str.isdigit, accession)))

    def remove_non_numeric_prefix(self, accession):
        return ''.join(filter(str.isdigit, accession))
    
    def process_single_protein_gpff_file(self, f, con, df_domain_types, df_interpro_domain_type_id):
        time_start = time.time()
        last_print_time = time_start
        counter = 0
        with gzip.open(f, "rt") as handle:  # "rt" stands for Read Text mode
            for record in SeqIO.parse(handle, "genbank"):
                msg = "\tStatus Update: Processed records:"
                counter, last_print_time = self.track_progress(counter, last_print_time, msg)
                # get protein-level information (ID, length, description, synonyms, corresponding transcript ID)
                n_protein_id = self.clean_id(record.id)
                protein_len = len(record.seq)
                protein_feature = [p for p in record.features if p.type == 'Protein'][0]
                protein_synonyms = protein_feature.qualifiers.get('note', [''])[0] # protein_feature.qualifiers.get('product', [''])[0] 
                cds_feature = [p for p in record.features if p.type == 'CDS'][0]
                t_id = self.clean_id(cds_feature.qualifiers.get("coded_by", [""])[0].split(":")[0]) ## find the corresponding transcript ID 
                if t_id not in self.transcript_map:
                    ensembl_transcript_id = self.transcript_refseq2ensembl.get(t_id, None)
                    if not ensembl_transcript_id or not ensembl_transcript_id in self.transcript_map:
                        logger.warning(f"Transcript ID {t_id} for protein {n_protein_id} not found in transcript map. Skipping protein.")
                        continue
                ensembl_transcript_id, ensembl_protein_id = self.get_record_ensemble_tran_prot(record)
                if not ensembl_protein_id:
                    ensembl_protein_id = self.protein_n2e.get(n_protein_id, None)
                self.output_db.add_row("Proteins", (n_protein_id, ensembl_protein_id, record.description, protein_synonyms, protein_len, t_id, ensembl_transcript_id))
                domains = query_domains(con, ensembl_protein_id, 1, protein_len) if ensembl_protein_id else []
                domains.extend(query_domains(con, n_protein_id, 1, protein_len) if n_protein_id else [])
                df_domains = pd.DataFrame(domains, columns=["db", "db_accession", "interpro_acc", "interpro_name", "aa_start", "aa_end"])
                df_domains.drop_duplicates(inplace=True)
                for idx, row in df_domains.iterrows():
                    if not row.db.lower() in ['cdd', 'pfam', 'smart', 'tigrfam']:
                        continue
                    type_id = df_interpro_domain_type_id[row.interpro_acc]
                    is_splice = self.handle_splice_domains(t_id, ensembl_transcript_id, row.interpro_name, row.aa_start, row.aa_end)
                    ext_ids = "; ".join([row.db_accession, row.interpro_acc])
                    self.output_db.add_row("DomainEvent", (n_protein_id, ensembl_protein_id, type_id, row.aa_start, 
                                                           row.aa_end, row.aa_start*3-2, row.aa_end*3, (row.aa_end-row.aa_start)*3, ext_ids  , is_splice, 1))
            self.output_db.flush_buffers(force=True)
            time_end = time.time()
            logger.info(f"Finished processing {f}. Time taken: {time_end - time_start:.2f} seconds.")


  
    def process_single_protein_gpff_file2(self, f, df_domain_types, accession_prefixes): 
        from dochap_download_domains import query_domains
        con = sqlite3.connect('/gpfs0/tals/projects/Analysis/ariel/DoChap/dochap_db/genomic_data/protein_domains.sqlite')  # TBD
        time_start = time.time()
        last_print_time = time_start
        counter = 0
        with gzip.open(f, "rt") as handle:  # "rt" stands for Read Text mode
            for record in SeqIO.parse(handle, "genbank"):
                msg = "\tStatus Update: Processed records:"
                counter, last_print_time = self.track_progress(counter, last_print_time, msg)
                # get protein-level information (ID, length, description, synonyms, corresponding transcript ID)
                n_protein_id = self.clean_id(record.id)
                protein_len = len(record.seq)
                protein_feature = [p for p in record.features if p.type == 'Protein'][0]
                protein_synonyms = protein_feature.qualifiers.get('note', [''])[0] # protein_feature.qualifiers.get('product', [''])[0] 
                cds_feature = [p for p in record.features if p.type == 'CDS'][0]
                t_id = self.clean_id(cds_feature.qualifiers.get("coded_by", [""])[0].split(":")[0]) ## find the corresponding transcript ID 
                if t_id not in self.transcript_map:
                    ensembl_transcript_id = self.transcript_refseq2ensembl.get(t_id, None)
                    if not ensembl_transcript_id or not ensembl_transcript_id in self.transcript_map:
                        logger.warning(f"Transcript ID {t_id} for protein {n_protein_id} not found in transcript map. Skipping protein.")
                        continue
                ensembl_transcript_id, ensembl_protein_id = self.get_record_ensemble_tran_prot(record)
                if not ensembl_protein_id:
                    ensembl_protein_id = self.protein_n2e.get(n_protein_id, None)
                self.output_db.add_row("Proteins", (n_protein_id, ensembl_protein_id, record.description, protein_synonyms, protein_len, t_id, ensembl_transcript_id))
                 
                # find region/domain features and extract CDD annotations
                for feature in record.features:
                    if feature.type != "Region":
                        continue 
                    region_name = feature.qualifiers.get("region_name", [None])[0]
                    if region_name is None:
                        continue
                               
                    description = feature.qualifiers.get("note", [""])[0]
                    # We only care about CDD-annotated regions
                    pssm_id, accession = self.parse_cdd_xref(feature.qualifiers.get("db_xref", []))
                    # Try to extract a named CDD accession from description
                    if not accession:
                        accession = self.extract_cdd_accession_from_note(description)
                    if not pssm_id and not accession:
                        logger.warning(f"Record {n_protein_id} has a Region {region_name} without a CDD/accession annotation. Skipping.")
                        continue
                    indices = df_domain_types.index[df_domain_types['pssm_id'] == int(pssm_id)].tolist() if pssm_id else []
                    if len(indices) == 0 and accession:
                        # try match number part of the accession to the corresponding column in domain types df (e.g. cd05711 -> match 5711 in cdd_id column)
                        id_column_name = accession_prefixes.get(accession[:2].lower(), None)
                        if id_column_name:
                            id_column_name += "_id" 
                            accession_id = self.get_numeric(accession) 
                            if accession_id != 0:
                                indices = df_domain_types.index[df_domain_types[id_column_name] == accession_id].tolist()
                    if len(indices) == 0:
                        logger.warning(f"Record {n_protein_id} has a Region {region_name} with CDD/accession annotation {pssm_id}/{accession} that was not found in the domain type map. Skipping.")
                        continue
                    if len(indices) > 1:
                        logger.warning(f"Record {n_protein_id} has a Region {region_name} with CDD/accession annotation {pssm_id}/{accession} that matched multiple entries in the domain type map. Skipping.")
                        continue
                    
                    if df_domain_types.loc[indices[0], 'counter'] == 0: # domain type not yet added to the database
                        self.domain_type_counter += 1
                        df_domain_types.loc[indices[0], 'counter'] = self.domain_type_counter
                        row = df_domain_types.loc[indices[0]]
                        # Insert 10 columns: type_id, name, other_name, description, CDD_id, cdd, pfam, smart, tigr, interpro
                        self.output_db.add_row("DomainType", (self.domain_type_counter, region_name, row.other_name, row.description, row.pssm_id, accession, row.pfam, row.smart, None, row.interpro))
                    row = df_domain_types.loc[indices[0]]
                    type_id  = int(row['counter'])
                    aa_start = int(feature.location.start) + 1  # 1-based
                    aa_end = int(feature.location.end)
                    is_splice = self.handle_splice_domains(t_id, ensembl_transcript_id, region_name, aa_start, aa_end)
                    ext_ids = []
                    for col in ['cdd', 'pfam', 'smart', 'tigr', 'interpro']:
                        if not pd.isna(row[col]) and row[col] != 'none':
                            ext_ids.append(str(row[col]))
                    ext_id = ';'.join(ext_ids)
                    self.output_db.add_row("DomainEvent", (n_protein_id, ensembl_protein_id, type_id, aa_start, aa_end, aa_start*3, aa_end*3, (aa_end-aa_start)*3, ext_id, is_splice, 1))
        self.output_db.flush_buffers(force=True)
        self.output_db.commit()
        con.close()
        logger.info(f"  Finished processing GPFF file: {f}. Total records: {counter}. Time elapsed: {time.time() - time_start:.2f} seconds")

    def handle_splice_domains(self, t_id, ensembl_transcript_id, region_name, aa_s, aa_e):
        if t_id not in self.transcript_map: return 0
        info = self.transcript_map[t_id]
        d_nuc_s, d_nuc_e = (aa_s * 3) + info['offset'], (aa_e * 3) + info['offset']
        hit_exons = []
        for i, (exon_feat, (abs_s, abs_e)) in enumerate(info['exons']):
            overlap_s, overlap_e = max(d_nuc_s, abs_s), min(d_nuc_e, abs_e)
            if overlap_s < overlap_e:
                hit_exons.append(i + 1)
                domain_type_id = self.domain_type_map.get(region_name, None)
                # transcript_refseq_id, transcript_ensembl_id, exon_order_in_transcript, type_id, total_length, domain_nuc_start, included_len, exon_num_in_domain 
                self.output_db.add_row("SpliceInDomains", (t_id, ensembl_transcript_id, i+1, overlap_s, domain_type_id, d_nuc_e-d_nuc_s, overlap_e-overlap_s, len(hit_exons)))
        return 1 if len(hit_exons) > 1 else 0

    
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
    
def run_build(input_path, specie, db_out):
    """Find GFF and GPFF files by their postfix patterns and create database."""
    # Find files matching the patterns
    input_path = Path(input_path)
    ncbi_input_path = input_path / specie / "refseq"
    ensembl_input_path = input_path / specie / "ensembl"
    ncbi_gff = find_file(ncbi_input_path, ["*_genomic.gff", "*_genomic.gff.gz"])
    ncbi_gpff_pattern = ncbi_input_path / "*.*.protein.gpff.gz"
    ensembl_gff = find_file(ensembl_input_path, [ "*.gff3", "*.gff3.gz"])
    interpro_domain_file = input_path / specie / "interpro.xml.gz"
    cddid_file = input_path / specie / "cddid.tbl.gz"
    
    logger.info(f"Found NCBI GFF: {ncbi_gff}")
    logger.info(f"Found Ensembl GFF: {ensembl_gff}")
    logger.info(f"NCBI GPFF pattern: {ncbi_gpff_pattern}")
    logger.info(f"InterPro domain file: {interpro_domain_file}")
    logger.info(f"CDD ID file: {cddid_file}")
    merger = DoChaPCBuilder(ncbi_gff=ncbi_gff, 
                           ensembl_gff=ensembl_gff, 
                           species=specie, 
                           ncbi_gpff_pattern=ncbi_gpff_pattern, 
                           interpro_domain_file=interpro_domain_file, 
                           cddid_file=cddid_file,
                           db_out=db_out)
    merger.create_db()
    
def main():
    run_build("/gpfs0/tals/projects/Analysis/ariel/DoChap/dochap_db/try1/genomic_data/", "H_sapiens", "unified_genome.db")
    if len(sys.argv) != 4:
        print("Usage: python gemini_download.py <input_path> <species> <output_db>")
        print("Example: python gemini_download.py /data/genomes H_sapiens unified_genome.db")
        sys.exit(1)
    
    input_path = sys.argv[1]
    species = sys.argv[2]
    output_db = sys.argv[3]
    
    run_build(input_path, species, output_db)
    
if __name__ == "__main__":
    main()
