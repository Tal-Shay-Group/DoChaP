import shutil
import sys
import time
import os
import logging
import pandas as pd
import numpy as np
import sqlite3
from Bio import SeqIO
import gffutils
import gemini_build_db

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class DoChaPCMerger:
    def __init__(self, ncbi_gff, ensembl_gff, species, ncbi_gpff, db_out="unified_genome.db"):
        # Initialize gffutils databases (in-memory for speed if files aren't massive)
        self.domain_type_set = set()  # To track unique domain types and avoid duplicates
        self.transcript_map = {} # {t_id: {'offset': int, 'exons': [(abs_s, abs_e, idx)]}}
        self.species = species
        self.ncbi_gpff = ncbi_gpff
        logger.info("Indexing GFF files...")
        if ncbi_gff.endswith('.gz'):
            ncbi_gff = self.decompress_gff(ncbi_gff)
        if ensembl_gff.endswith('.gz'):
            ensembl_gff = self.decompress_gff(ensembl_gff)
        self.n_db = self.gff_to_sqlite(ncbi_gff, ncbi_gff + ".db")
        self.e_db = self.gff_to_sqlite(ensembl_gff, ensembl_gff + ".db")
        logger.info("Indexing GFF files...Done")

        # 2. Setup Unified SQL Database
        self.output_db = gemini_build_db.DoChaPBuilder(db_out)
        self.output_db.connect()

    def clean_id(self, identifier):
        if not identifier or pd.isna(identifier) or identifier == "": 
            return ''
        id = str(identifier)
        tags = ['gene-', 'rna-', 'transcript-', 'protein-', 'gene:', 'rna:', 'transcript:', 'protein:']
        for tag in tags:
            if tag in id:
                return id.removeprefix(tag).split('.')[0]  # Remove version suffix if present
        return id.split('.')[0]  # Remove version suffix if present

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
        synonyms += e_gene.attributes.get('Alias', []) if e_gene else []
        synonyms += e_gene.attributes.get('external_name', []) if e_gene else []
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

    def match_gene(self, e_db_index, e_db, symbol, gene_id, ensembl_id, n_gene):
        match_method = "x"
        e_gene = None
        if symbol:
            e_gene = e_db_index.get(symbol, None)
            if e_gene:
                match_method = "Symbol"
        if not e_gene and gene_id:
            e_gene = e_db_index.get(gene_id, None)
            if e_gene:
                match_method = "gene_id"
        if not e_gene and ensembl_id:
            e_gene = e_db_index.get(ensembl_id, None)
            if e_gene:
                match_method = "ensembl_id"
                

        # --- PHASE 2: SPATIAL FALLBACK ---
        if not e_gene:
            # Search Ensembl for any gene overlapping this NCBI gene's coordinates
            # Note: Ensure chromosome names match (e.g., '1' vs 'NC_006839.7')
            overlaps = list(e_db.region(
                seqid=n_gene.chrom, 
                start=n_gene.start, 
                end=n_gene.end, 
                featuretype='gene'
            ))
            
            if overlaps:
                # If multiple overlaps, prioritize by symbol match, otherwise take the first
                symbol_match = [o for o in overlaps if o.attributes.get('Name', [None])[0] == symbol]
                e_gene = symbol_match[0] if symbol_match else overlaps[0]
                match_method = "Spatial"
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
            self.output_db.add_row('Genes', ('', ensembl_id, '', synonyms, e_gene.seqid, e_gene.strand, self.species))
            self.add_transcripts(None, e_gene)
        logger.info(f"Processed {count} Ensembl genes. Skipped {count_alternative} on alternative chromosomes and {count_non_coding} non-protein-coding genes.")
    
    
    def traverse_ncbi_genes(self):
        logger.info(f"Traversing NCBI genes")
        matches = []
        count = 0
        count_alternative = 0
        count_non_coding = 0
        e_gene_handled_ids = set()
        e_db_index = self.build_gene_name_index(self.e_db)  # Build an index for quick name-based lookups in Ensembl
        for n_gene in self.n_db.features_of_type('gene'):
            n_gene_id = self.clean_id(n_gene.id)    
            count += 1
            if count % 1000 == 0:
                logger.info(f"Processed {count} genes...")
            if not self.is_primary_chromosome(self.n_db, self.clean_id(n_gene.seqid)):
                logger.debug(f"Skipping alternative chromosome {n_gene.seqid} for gene {n_gene_id}")
                count_alternative += 1
                continue
            if not self.is_gene_protein_coding(n_gene):    
                logger.debug(f"Skipping non-protein-coding gene {n_gene_id} ({n_gene.attributes.get('Name', [''])[0]})")
                count_non_coding += 1
                continue
            attrs = n_gene.attributes
            symbol = attrs.get('gene', [None])[0]
            
            # --- PHASE 1: ID BRIDGE ---
            dbxrefs = attrs.get('Dbxref', [])
            gene_id = next((x.split(':')[1] for x in dbxrefs if 'GeneID' in x), None)
            ensembl_id = next((x.split(':')[1] for x in dbxrefs if 'Ensembl' in x), None)
            e_gene, match_method = self.match_gene(e_db_index, self.e_db, symbol, gene_id, ensembl_id, n_gene)
            
            if e_gene:
                ensembl_id = self.clean_id(e_gene.id)
                synonyms = ";".join(self.get_gene_synonyms(e_gene, n_gene))
                e_gene_handled_ids.add(ensembl_id)
            else:
                ensembl_id = ''  # No Ensembl match
                synonyms = ";".join(self.get_gene_synonyms(None, n_gene))
            self.output_db.add_row('Genes', (gene_id, ensembl_id, symbol, synonyms, n_gene.chrom, n_gene.strand, self.species))
            self.add_transcripts(n_gene, e_gene) 
            matches.append((n_gene_id, ensembl_id, gene_id, symbol, match_method)) 
        logger.info(f"\tSkipped {count_alternative} genes on alternative chromosomes.")
        logger.info(f"\tSkipped {count_non_coding} non-protein-coding genes.")
        logger.info(f"\tTotal genes processed: {count-count_alternative-count_non_coding} (matches: {len(matches)})")
        return e_gene_handled_ids, matches

    def create_db(self):
        e_gene_handled_ids, matches = self.traverse_ncbi_genes()        
        self.add_missing_ensembl_genes(e_gene_handled_ids)
        
        df = pd.DataFrame(matches, columns=['NCBI_id', 'EnsemblID', 'GeneID', 'Symbol', 'MatchMethod'])
        df.to_csv(f"{self.species}_gene_matches.csv", index=False)
        self.output_db.flush_buffers(force=True)
        self.output_db.commit()

        self.process_refseq_proteins()
        self.output_db.create_index()
        self.output_db.close()
                
        logger.info(f"Merging {self.species} complete.")
        

    def is_protein_coding(self, db, transcript):
        # Count how many CDS features belong to this transcript
        cds_count = len(list(db.children(transcript, featuretype='CDS')))
        return cds_count > 0

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
        e_tx_id = self.clean_id(e_tx.id) if e_tx else ''
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
                e_protein_id = self.clean_id(e_cds_list[0].attributes.get('protein_id', [''])[0])    
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

    def add_transcript(self, e_tx, n_tx):
        e_tx_id = self.clean_id(e_tx.id) if e_tx else ''
        n_tx_id = self.clean_id(n_tx.id) if n_tx else ''
        n_gene_id = self.clean_id(n_tx.attributes.get('Parent', [None])[0]) if n_tx else ''
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
        abs_length = abs_cds_stop[-1] if abs_cds_stop else 0
        n_protein_id, e_protein_id = self.add_protein(e_tx, n_tx, abs_length / 3 +1)
        
        self.transcript_map[self.clean_id(transcript.id)] = {'offset': offset, 'exons': list(zip(exons, abs_coords))}
        self.output_db.add_row("Transcripts",(n_tx_id, e_tx_id, transcript.start, transcript.end, cds_min, cds_max, len(exons), n_gene_id, e_gene_id, n_protein_id, e_protein_id))

        for idx, exon in enumerate(exons):
            self.output_db.add_row("Exons", (n_gene_id, e_gene_id, exon.start, exon.end))
            # transcript_refseq_id, transcript_ensembl_id, order_in_transcript, genomic_start_tx, genomic_end_tx, abs_start_CDS, abs_end_CDS
            self.output_db.add_row("Transcript_Exon", (n_tx_id, e_tx_id, idx + 1, exon.start, exon.end, abs_cds_start[idx], abs_cds_stop[idx]))

    def add_transcripts(self, n_gene, e_gene):
        matches = {} # Maps Ensembl transcript IDs to matched NCBI transcript objects
        e_transcripts =[] # list of all protein-coding transcripts for this Ensembl gene
        e_map = {} # Maps exon fingerprints to Ensembl transcript  for quick lookup
        if e_gene:
            for e_tx in self.e_db.children(e_gene.id, featuretype=['transcript', 'mRNA']):
                if self.is_protein_coding(self.e_db, e_tx):
                    e_transcripts.append(e_tx)
            e_map = {self.get_exon_fingerprint(self.e_db, tx): tx for tx in e_transcripts}
        if n_gene:    
            for n_tx in self.n_db.children(n_gene, featuretype=['transcript', 'mRNA']):
                if not self.is_protein_coding(self.n_db, n_tx):
                    continue
                
                n_fingerprint = self.get_exon_fingerprint(self.n_db, n_tx)
                # Check for an exact exon-for-exon match
                matched_e_tx = e_map.get(n_fingerprint)
                if matched_e_tx:
                    logger.debug(f"NCBI transcript match found for  {n_tx.id} with Ensembl transcript {matched_e_tx.id}")
                    
                    matches[matched_e_tx] = n_tx
                else:           
                    logger.debug(f"NCBI transcript no match found for  {n_tx.id} (fingerprint: {n_fingerprint})")
                self.add_transcript(matched_e_tx, n_tx)
        for e_tx in e_map.values():
            if e_tx not in matches:
                self.add_transcript(e_tx, None)
                logger.debug(f"Ensembl transcript no match found for  {e_tx.id}.")
        return

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
    
    def process_refseq_proteins(self):
        logger.info(f"  Processing RefSeq GPFF for proteins and domains: {self.ncbi_gpff}")
        PRINT_INTERVAL = 300  # 5 minutes
        time_start = time.time()
        last_print_time = time_start
        self.output_db.connect()
        counter = 0
        for rec in SeqIO.parse(self.ncbi_gpff, "genbank"):
            counter += 1
            if counter % 1000 == 0:
                self.output_db.flush_buffers(force=False)
            current_time = time.time()
            if current_time - last_print_time >= PRINT_INTERVAL:
                logger.info(f"\tStatus Update: Processed {counter} records. Time: {time.ctime()}")
                last_print_time = current_time
            p_ref, t_id = self.clean_id(rec.id), None
            for feat in rec.features:
                if feat.type == "CDS":
                    t_id = self.clean_id(feat.qualifiers.get("coded_by", [""])[0].split(":")[0])
                    break
            self.output_db.add_row("Proteins", (p_ref, None, rec.description, len(rec.seq), "", t_id, None))
            for feat in rec.features:
                if feat.type in ["Region", "Domain"]:
                    reg_name = feat.qualifiers.get("region_name", ["Unknown"])[0]
                    regID = hash(reg_name)
                    if regID not in self.domain_type_set:
                        # Parse db_xref to extract database-specific IDs
                        db_xrefs = feat.qualifiers.get("db_xref", [])
                        cdd_id, cdd_val, pfam_val, smart_val, interpro_val = None, None, None, None, None
                        
                        for xref in db_xrefs:
                            if xref.startswith("CDD:"):
                                cdd_id = xref.split(":", 1)[1]
                                cdd_val = cdd_id
                            elif xref.startswith("InterPro:"):
                                interpro_val = xref.split(":", 1)[1]
                            elif xref.startswith("Pfam:"):
                                pfam_val = xref.split(":", 1)[1]
                            elif xref.startswith("SMART:"):
                                smart_val = xref.split(":", 1)[1]
                        
                        # Insert all 10 columns: type_id, name, other_name, description, CDD_id, cdd, pfam, smart, tigr, interpro
                        self.output_db.add_row("DomainType", (regID, reg_name, None, feat.qualifiers.get("note", [""])[0], cdd_id, cdd_val, pfam_val, smart_val, None, interpro_val))
                        self.domain_type_set.add(regID)
                    aa_s, aa_e = int(feat.location.start), int(feat.location.end)
                    is_splice = self.handle_splice_domains(t_id, p_ref, None, regID, aa_s, aa_e)
                    self.output_db.add_row("DomainEvent", (p_ref, None, regID, aa_s, aa_e, aa_s*3, aa_e*3, (aa_e-aa_s)*3, "", is_splice, 1))
        self.output_db.flush_buffers(force=True)
        self.output_db.commit()
        logger.info(f"  Finished processing GPFF. Total records: {counter}. Time elapsed: {time.time() - time_start:.2f} seconds")

    def handle_splice_domains(self, t_id, p_ref, p_ens, regID, aa_s, aa_e):
        if t_id not in self.transcript_map: return 0
        info = self.transcript_map[t_id]
        d_nuc_s, d_nuc_e = (aa_s * 3) + info['offset'], (aa_e * 3) + info['offset']
        hit_exons = []
        for i, (exon_feat, (abs_s, abs_e)) in enumerate(info['exons']):
            overlap_s, overlap_e = max(d_nuc_s, abs_s), min(d_nuc_e, abs_e)
            if overlap_s < overlap_e:
                hit_exons.append(i + 1)
                self.output_db.add_row("SpliceInDomains", (p_ref, p_ens, i+1, overlap_s, regID, d_nuc_e-d_nuc_s, overlap_e-overlap_s, len(hit_exons)))
        return 1 if len(hit_exons) > 1 else 0

    def process_ensembl_domains(self, sp_dir, sp_name):
        logger.info(f"  Processing Ensembl domain annotations for {sp_name}...")
        external_dbs = ["interpro", "pfam", "smart", "tigrfams"]
        PRINT_INTERVAL = 300  # 5 minutes
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
                if current_time - last_print_time >= PRINT_INTERVAL:
                    logger.info(f"\tStatus Update: Processed {counter} {ext} records. Time: {time.ctime()}")
                    last_print_time = current_time
                p_id = self.clean_id(row.protein_stable_id) 
                t_id = self.clean_id(row.transcript_stable_id)
                reg_name = row.domain_id
                regID = hash(reg_name)
                if regID not in self.domain_type_set:
                    # Insert all 10 columns, populate the appropriate source column
                    pfam_val = reg_name if ext == 'pfam' else None
                    smart_val = reg_name if ext == 'smart' else None
                    tigr_val = reg_name if ext == 'tigrfams' else None
                    interpro_val = reg_name if ext == 'interpro' else None
                    self.buffers["DomainType"].append((regID, reg_name, None, row.description, None, None, pfam_val, smart_val, tigr_val, interpro_val))
                    self.domain_type_set.add(regID)
                aa_s, aa_e = int(row.start), int(row.end)
                is_splice = self.handle_splice_domains(t_id, None, p_id, regID, aa_s, aa_e)
                self.output_db.add_row("DomainEvent", (None, p_id, regID, aa_s, aa_e, aa_s*3, aa_e*3, (aa_e-aa_s)*3, row.id, is_splice, 1))
            logger.info(f"    Finished processing {ext} domains. Total records: {counter}. Time elapsed: {time.time() - time_start:.2f} seconds}")
            self.output_db.flush_buffers(force=True)
            self.output_db.commit()


    # --- PASS 3: Multi-Species Orthology ---
    def process_multi_species_orthology(self, file_path, source_species, gene_symbol_cache):
        if not os.path.exists(file_path): return
        logger.info(f"  Parsing orthology file: {file_path}")
        PRINT_INTERVAL = 300  # 5 minutes
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

        self.connect()
        self.cur.execute("BEGIN TRANSACTION;")
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
                if current_time - last_print_time >= PRINT_INTERVAL:
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

            

def main():
    #create_db(source_db=sys.argv[1], target_db=sys.argv[2], reference_genome=sys.argv[3] if len(sys.argv) > 3 else None)
    merger = DoChaPCMerger(
        ncbi_gff="GCF_000004195.4_UCB_Xtro_10.0_genomic.gff.gz", 
        ensembl_gff="Xenopus_tropicalis.UCB_Xtro_10.0.115.gff3.gz", 
        species="X_tropicalis", 
        ncbi_gpff='genomic_data/X_tropicalis/refseq/1/GCF_000004195.4_UCB_Xtro_10.0_protein.gpff',
        db_out="unified_genome.db")
    merger.create_db()
if __name__ == "__main__":
    main()
