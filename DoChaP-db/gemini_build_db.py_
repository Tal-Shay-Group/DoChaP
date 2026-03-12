import os
import re
import time
import sqlite3
import gffutils
import pandas as pd
import requests
from io import StringIO
from Bio import SeqIO
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

gff_verbose_counter = 0
def gff_verbose(feature):
    global gff_verbose_counter
    if gff_verbose_counter % 500000 == 0:
        print(f"Processed {gff_verbose_counter} lines...", flush=True)
    gff_verbose_counter += 1
    return feature

class DoChaPBuilder:
    def __init__(self, db_name):
        self.db_name = db_name + ".sqlite" if not db_name.endswith(".sqlite") else db_name
        self.con = None
        self.cur = None
        self.BATCH_SIZE = 25000
        self.buffers = {
            "Genes": [], "Transcripts": [], "Exons": [], 
            "Transcript_Exon": [], "Proteins": [], 
            "DomainEvent": [], "DomainType": [], 
            "SpliceInDomains": [], "Orthology": []
        }
        self.gene_set = set()
        self.exon_set = set()
        self.domain_type_set = set()
        self.transcript_map = {} # {t_id: {'offset': int, 'exons': [(abs_s, abs_e, idx)]}}
        self.connect()
        self._create_tables_db()

    def _apply_pragmas(self):
        self.cur.execute("PRAGMA journal_mode = MEMORY;")
        self.cur.execute("PRAGMA synchronous = OFF;")
        self.cur.execute("PRAGMA cache_size = 100000;")
        self.cur.execute("PRAGMA temp_store = MEMORY;")
        self.cur.execute("PRAGMA mmap_size = 30000000000;")

    def connect(self):
        if self.con:
            return
        self.con = sqlite3.connect(self.db_name)
        self.cur = self.con.cursor()
        self._apply_pragmas()
    
    
    def commit(self):    
        self.con.commit()  

    def close(self):    
        self.con.commit()    
        self.con.close()
        self.con = None
        self.cur = None
        
    def add_row(self, table, data):
        self.buffers[table].append(data)
        if len(self.buffers[table]) >= self.BATCH_SIZE:
            self.flush_buffers(specific_table=table, force=True)

    def _create_tables_db(self):
        print("Creating database: {}...".format(self.db_name))
        self.connect()
        self.create_gene_table()
        self.create_transcript_table()
        self.create_exon_table()
        self.create_transcript_exon_table()
        self.create_protein_table()
        self.create_domain_table()
        self.create_domain_event_table()
        self.create_splice_in_domain_table()
        self.create_orthology_table()
        self.con.commit()
        print("Database created successfully.")
    
    def create_gene_table(self):
        self.cur.executescript('DROP TABLE IF EXISTS Genes;')
        print('Creating the table: Genes')
        self.cur.execute('''
                    CREATE TABLE Genes(
                            gene_GeneID_id TEXT UNIQUE,
                            gene_ensembl_id TEXT UNIQUE,
                            gene_symbol TEXT,
                            synonyms TEXT,
                            chromosome TEXT,
                            strand TEXT,
                            specie TEXT, 
                            PRIMARY KEY(gene_GeneID_id, gene_ensembl_id, gene_symbol)
                            );'''
                    )
    def create_transcript_table(self):
        self.cur.executescript("DROP TABLE IF EXISTS Transcripts;")
        print('Creating the table: Transcripts')
        self.cur.execute('''
                    CREATE TABLE Transcripts(
                            transcript_refseq_id TEXT UNIQUE,
                            transcript_ensembl_id TEXT UNIQUE,
                            tx_start INTEGER,
                            tx_end INTEGER,
                            cds_start INTEGER,
                            cds_end INTEGER,
                            exon_count INTEGER,
                            gene_GeneID_id TEXT,                        
                            gene_ensembl_id TEXT,
                            protein_refseq_id TEXT,
                            protein_ensembl_id TEXT,
                            PRIMARY KEY (transcript_refseq_id, transcript_ensembl_id),
                            FOREIGN KEY(gene_GeneID_id, gene_ensembl_id) REFERENCES Genes(gene_GeneID_id, gene_ensembl_id)
                            );'''
                    )
    def create_exon_table(self):
        self.cur.executescript("DROP TABLE IF EXISTS Exons;")
        print('Creating the table: Exons')
        self.cur.execute('''
                    CREATE TABLE Exons(
                            gene_GeneID_id TEXT,
                            gene_ensembl_id TEXT,        
                            genomic_start_tx INTEGER,
                            genomic_end_tx INTEGER,
                            PRIMARY KEY (gene_GeneID_id, gene_ensembl_id, genomic_start_tx, genomic_end_tx),
                            FOREIGN KEY(gene_GeneID_id, gene_ensembl_id) REFERENCES Genes(gene_GeneID_id, gene_ensembl_id)
                            );'''
                    )

        self.cur.executescript("DROP TABLE IF EXISTS Transcript_Exon;")
    
    def create_transcript_exon_table(self):
        print('Creating the table: Transcript_Exon')
        self.cur.execute('''
                    CREATE TABLE Transcript_Exon(
                            transcript_refseq_id TEXT,
                            transcript_ensembl_id TEXT,
                            order_in_transcript INTEGER,
                            genomic_start_tx INTEGER,
                            genomic_end_tx INTEGER,
                            abs_start_CDS INTEGER,
                            abs_end_CDS INTEGER,
                            PRIMARY KEY(transcript_refseq_id, transcript_ensembl_id, order_in_transcript),
                            FOREIGN KEY(transcript_refseq_id, transcript_ensembl_id) 
                                REFERENCES Transcripts(transcript_refseq_id, transcript_ensembl_id)
                            );'''
                    )
    def create_protein_table(self):
        self.cur.executescript("DROP TABLE IF EXISTS Proteins;")
        print('Creating the table: Proteins')
        self.cur.execute('''
                    CREATE TABLE Proteins(
                            protein_refseq_id TEXT UNIQUE,
                            protein_ensembl_id TEXT UNIQUE,
                            description TEXT,
                            synonyms TEXT,
                            length INTEGER,
                            transcript_refseq_id TEXT,
                            transcript_ensembl_id TEXT,
                            PRIMARY KEY(protein_refseq_id, protein_ensembl_id)
                            );'''
                    )
    def create_domain_table(self):
        self.cur.executescript("DROP TABLE IF EXISTS DomainType;")
        print('Creating the table: DomainType')
        self.cur.execute('''
                    CREATE TABLE DomainType(
                            type_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
                            name TEXT,
                            other_name TEXT,
                            description TEXT,
                            CDD_id TEXT,
                            cdd TEXT,
                            pfam TEXT,
                            smart TEXT,
                            tigr TEXT,
                            interpro TEXT
                            );'''
                    )
    
    def create_domain_event_table(self):
        self.cur.executescript("DROP TABLE IF EXISTS DomainEvent;")
        print('Creating the table: DomainEvent')
        self.cur.execute('''
                    CREATE TABLE DomainEvent(
                            protein_refseq_id TEXT,
                            protein_ensembl_id TEXT,
                            type_id INTEGER,
                            AA_start INTEGER,
                            AA_end INTEGER,
                            nuc_start INTEGER,
                            nuc_end INTEGER,
                            total_length INTEGER,
                            ext_id TEXT,
                            splice_junction BOOLEAN,
                            complete_exon BOOLEAN,
                            PRIMARY KEY(protein_refseq_id, protein_ensembl_id, type_id, AA_start, total_length),
                            FOREIGN KEY(type_id) REFERENCES DomainType(type_id),
                            FOREIGN KEY(protein_refseq_id, protein_ensembl_id) 
                                REFERENCES Proteins(protein_refseq_id, protein_ensembl_id)
                            );'''
                    )
    def create_splice_in_domain_table(self):
        self.cur.executescript("DROP TABLE IF EXISTS SpliceInDomains;")
        print('Creating the table: SpliceInDomains')
        self.cur.execute("""
                    CREATE TABLE SpliceInDomains(
                            transcript_refseq_id TEXT,
                            transcript_ensembl_id TEXT,
                            exon_order_in_transcript INTEGER,
                            type_id INTEGER,
                            total_length INTEGER,
                            domain_nuc_start INTEGER,
                            included_len INTEGER,
                            exon_num_in_domain INTEGER,
                            PRIMARY KEY (transcript_refseq_id, transcript_ensembl_id, exon_order_in_transcript, type_id,\
                            total_length, domain_nuc_start),
                            FOREIGN KEY(transcript_refseq_id, transcript_ensembl_id) 
                                REFERENCES Transcripts(transcript_refseq_id, transcript_ensembl_id),
                            FOREIGN KEY(type_id) REFERENCES DomainType(type_id)
                            );"""
                    )

    def create_orthology_table(self):    
        self.cur.executescript("DROP TABLE IF EXISTS Orthology;")
        print('Creating the table: Orthology')
        self.cur.execute("""
                    CREATE TABLE Orthology(
                            A_ensembl_id TEXT,
                            A_GeneSymb TEXT,
                            A_species TEXT,
                            B_ensembl_id TEXT,
                            B_GeneSymb TEXT,
                            B_species TEXT,
                            PRIMARY KEY (A_ensembl_id, B_ensembl_id)
                            );"""
                    )
    
    def create_index(self):
        """ Creates index for for efficient searches"""
        t0 = time.time()
        if not self.con:
            self.connect()
        
        self.cur.execute('''CREATE INDEX IF NOT EXISTS geneTableIndexBySpecies ON Genes(specie);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS geneTableIndexByEnsembl ON Genes(gene_ensembl_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS geneTableIndexByGeneID ON Genes(gene_GeneID_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS transcriptTableIndexByGene ON Transcripts(gene_GeneID_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS transcriptTableIndexByGeneEnsembl ON Transcripts(gene_ensembl_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS exonsInTranscriptsTableIndexByTranscripts ON Transcript_Exon(transcript_refseq_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS exonInTranscriptsTableIndexByEnsembl ON Transcript_Exon(transcript_ensembl_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS proteinTableIndexByTranscriptRefseq ON Proteins(transcript_refseq_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS proteinTableIndexByTranscriptEnsembl ON Proteins(transcript_ensembl_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS domainEventsTableIndexByProtein ON DomainEvent(protein_refseq_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS domainEventsTableIndexByEnsembl ON DomainEvent(protein_ensembl_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS domainEventsTableIndexByType ON DomainEvent(type_id);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS orthologyTableIndexBySpeciesA ON Orthology(A_species);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS orthologyTableIndexBySpeciesB ON Orthology(B_species);''')
        self.cur.execute('''CREATE INDEX IF NOT EXISTS orthologyTableIndexByGeneB ON Orthology(B_ensembl_id);''')
        self.con.commit()

        print(f"Index creation completed in {time.time() - t0:.2f} seconds")
        t1 = time.time()
        self.cur.execute("VACUUM;")
        print(f"VACUUM completed in {time.time() - t1:.2f} seconds")
        t2 = time.time()
        self.cur.execute("ANALYZE;")
        self.con.commit() 
        print(f"ANALYZE completed in {time.time() - t2:.2f} seconds")

    def clean_id(self, identifier):
        if not identifier or pd.isna(identifier) or identifier == "": 
            return None
        id = str(identifier)
        if ':' in id:
            return id.split(':')[-1].split('.')[0]
        if '-' in id:
            return id.split('-')[-1].split('.')[0]
        return id
    

    def flush_buffers(self, specific_table=None, force=False):
        queries = {
            "Genes": "INSERT OR IGNORE INTO Genes (gene_GeneID_id, gene_ensembl_id, gene_symbol, synonyms, chromosome, strand, specie) VALUES (?,?,?,?,?,?,?)",
            "Transcripts": "INSERT OR IGNORE INTO Transcripts (transcript_refseq_id, transcript_ensembl_id, tx_start, tx_end, cds_start, cds_end, exon_count, gene_GeneID_id, gene_ensembl_id, protein_refseq_id, protein_ensembl_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            "Exons": "INSERT OR IGNORE INTO Exons (gene_GeneID_id, gene_ensembl_id, genomic_start_tx, genomic_end_tx) VALUES (?,?,?,?)",
            "Transcript_Exon": "INSERT OR IGNORE INTO Transcript_Exon (transcript_refseq_id, transcript_ensembl_id, order_in_transcript, genomic_start_tx, genomic_end_tx, abs_start_CDS, abs_end_CDS) VALUES (?,?,?,?,?,?,?)",
            "Proteins": "INSERT OR IGNORE INTO Proteins (protein_refseq_id, protein_ensembl_id, description, synonyms, length, transcript_refseq_id, transcript_ensembl_id) VALUES (?,?,?,?,?,?,?)",
            "DomainType": "INSERT INTO DomainType (type_id, name, other_name, description, CDD_id, cdd, pfam, smart, tigr, interpro) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "DomainEvent": "INSERT OR IGNORE INTO DomainEvent (protein_refseq_id, protein_ensembl_id, type_id, AA_start, AA_end, nuc_start, nuc_end, total_length, ext_id, splice_junction, complete_exon) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            "SpliceInDomains": "INSERT OR IGNORE INTO SpliceInDomains (transcript_refseq_id, transcript_ensembl_id, exon_order_in_transcript, domain_nuc_start, type_id, total_length, included_len, exon_num_in_domain) VALUES (?,?,?,?,?,?,?,?)",
            "Orthology": "INSERT OR IGNORE INTO Orthology (A_ensembl_id, A_GeneSymb, A_species, B_ensembl_id, B_GeneSymb, B_species) VALUES (?,?,?,?,?,?)"
        }
        if specific_table:
            data = self.buffers[specific_table]
            if data and (len(data) >= self.BATCH_SIZE or force):
                self.cur.executemany(queries[specific_table], data)
                self.buffers[specific_table] = []
        else:
            for table, data in self.buffers.items():
                if data and (len(data) >= self.BATCH_SIZE or force):
                    self.cur.executemany(queries[table], data)
                    self.buffers[table] = []

    def calculate_abs_coords(self, exons, strand):
        abs_coords = []
        offset = 0
        ordered = exons if strand == '+' else exons[::-1]
        for e in ordered:
            length = e.end - e.start + 1
            abs_coords.append((offset + 1, offset + length))
            offset += length
        return abs_coords if strand == '+' else abs_coords[::-1]

    def _handle_splice_domains(self, t_id, p_ref, p_ens, regID, aa_s, aa_e):
        if t_id not in self.transcript_map: return 0
        info = self.transcript_map[t_id]
        d_nuc_s, d_nuc_e = (aa_s * 3) + info['offset'], (aa_e * 3) + info['offset']
        hit_exons = []
        for i, (exon_feat, (abs_s, abs_e)) in enumerate(info['exons']):
            overlap_s, overlap_e = max(d_nuc_s, abs_s), min(d_nuc_e, abs_e)
            if overlap_s < overlap_e:
                hit_exons.append(i + 1)
                self.buffers["SpliceInDomains"].append((p_ref, p_ens, i+1, overlap_s, regID, d_nuc_e-d_nuc_s, overlap_e-overlap_s, len(hit_exons)))
        return 1 if len(hit_exons) > 1 else 0

    

    # --- PASS 1: GFF Structure ---
    def process_gff(self, gff_path, species, source):
        global gff_verbose_counter  
        print(f"  Processing {source} GFF...")
        db_temp = gff_path + ".db"
        
        
        # Reuse existing gffutils database if available
        if os.path.exists(db_temp):
            print(f"    Using existing gffutils database: {db_temp}")
            db = gffutils.FeatureDB(db_temp)
        else:
            print(f"    Creating gffutils database (this may take several minutes for large genomes)...")
            db_start = time.time()
            gff_verbose_counter = 0
            db_temp_temp = Path('/tmp/') / f'{species}.db'
            print('     Reading gff file: {}'.format(gff_path))
            print('    Temporary database will be created at: {}'.format(db_temp_temp))
            try:
                db = gffutils.create_db(str(gff_path), dbfn=str(db_temp_temp) , force=True, merge_strategy='error', keep_order=True,transform=gff_verbose)
            except Exception as e:
                print(f"    Error creating gffutils database: {e}")
                os.rename(db_temp_temp, db_temp)  # Move to final location after creation
                raise
            print(f"    gffutils database created in {time.time() - db_start:.2f} seconds")
        
        PRINT_INTERVAL = 60 # 1 minute 
        time_start = time.time()
        last_print_time = time_start
        self.connect()
        
        self.cur.execute("BEGIN TRANSACTION;")
        counter = 0
        for gene in db.features_of_type('gene'):
            counter += 1
            if counter % 1000 == 0:
                self.flush_buffers(force=False)
            current_time = time.time()
            if current_time - last_print_time >= PRINT_INTERVAL:
                print(f"\tStatus Update: Processed {counter} genes. Time: {time.ctime()}")
                last_print_time = current_time
            g_id = self.clean_id(gene.id)
            g_ref, g_ens = (g_id, None) if source == 'refseq' else (None, g_id)
            if source == 'refseq':
                dbxrefs = gene.attributes.get('Dbxref', [])
                for dbxref in dbxrefs:
                    if 'Ensembl:' in dbxref:
                        g_ens = self.clean_id(dbxref.replace("Ensembl:", ""))
                        break
            
            hash_gene_ref =  hash(g_ref) if g_ref else None
            hash_gene_ens = hash(g_ens) if g_ens else None
            if hash_gene_ref not in self.gene_set and hash_gene_ens not in self.gene_set:
                self.buffers["Genes"].append((g_ref, g_ens, gene.attributes.get('Name', [g_id])[0], "", gene.chrom, gene.strand, species))
                if hash_gene_ref: 
                    self.gene_set.add(hash_gene_ref)
                if hash_gene_ens: 
                    self.gene_set.add(hash_gene_ens)

            # Process all child transcripts
            for t in db.children(gene, featuretype=('mRNA', 'transcript'), order_by='start'):
                t_id = self.clean_id(t.id)
                t_ref, t_ens = (t_id, None) if source == 'refseq' else (None, t_id)
                
                # Get exons and CDS in one iteration each
                exons = list(db.children(t, featuretype='exon', order_by='start'))
                if not exons:  # Skip transcripts with no exons
                    continue
                    
                abs_c = self.calculate_abs_coords(exons, t.strand)
                cds_list = list(db.children(t, featuretype='CDS', order_by='start'))
                c_s = min(c.start for c in cds_list) if cds_list else t.start
                c_e = max(c.end for c in cds_list) if cds_list else t.end
                offset = (c_s - t.start) if t.strand == '+' else (t.end - c_e)
                self.transcript_map[t_id] = {'offset': offset, 'exons': list(zip(exons, abs_c))}
                
                # Extract protein ID
                p_ref_id = None
                p_ens_id = None
                if source == 'refseq':
                    protein_ids = t.attributes.get('protein_id', [])
                    if protein_ids:
                        p_ref_id = self.clean_id(protein_ids[0])
                else:
                    protein_ids = t.attributes.get('protein_id', [])
                    if protein_ids:
                        p_ens_id = self.clean_id(protein_ids[0])
                
                self.buffers["Transcripts"].append((t_ref, t_ens, t.start, t.end, c_s, c_e, len(exons), g_ref, g_ens, p_ref_id, p_ens_id))
                
                # Process exons
                for i, (exon, coords) in enumerate(zip(exons, abs_c)):
                    ex_tuple = (g_ref, g_ens, exon.start, exon.end)
                    ex_hash = hash(ex_tuple)
                    if ex_hash not in self.exon_set:
                        self.buffers["Exons"].append(ex_tuple)
                        self.exon_set.add(ex_hash)
                    self.buffers["Transcript_Exon"].append((t_ref, t_ens, i+1, exon.start, exon.end, coords[0], coords[1]))
            self.flush_buffers(force=True)
            self.commit()
            print(f"  Finished processing GFF. Total genes: {counter}. Time elapsed: {time.time() - time_start:.2f} seconds")
        
        # Keep temp database for reuse instead of deleting
        # os.remove(db_temp)

    # --- PASS 2: Proteins & Domains ---
    def process_refseq_proteins(self, gpff_path):
        print(f"  Processing RefSeq GPFF for proteins and domains: {gpff_path}")
        PRINT_INTERVAL = 300  # 5 minutes
        time_start = time.time()
        last_print_time = time_start
        self.connect()
        self.cur.execute("BEGIN TRANSACTION;")
        counter = 0
        for rec in SeqIO.parse(gpff_path, "genbank"):
            counter += 1
            if counter % 1000 == 0:
                self.flush_buffers(force=False)
            current_time = time.time()
            if current_time - last_print_time >= PRINT_INTERVAL:
                print(f"\tStatus Update: Processed {counter} records. Time: {time.ctime()}")
                last_print_time = current_time
            p_ref, t_id = self.clean_id(rec.id), None
            for feat in rec.features:
                if feat.type == "CDS":
                    t_id = self.clean_id(feat.qualifiers.get("coded_by", [""])[0].split(":")[0])
                    break
            self.buffers["Proteins"].append((p_ref, None, rec.description, len(rec.seq), "", t_id, None))
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
                        self.buffers["DomainType"].append((regID, reg_name, None, feat.qualifiers.get("note", [""])[0], cdd_id, cdd_val, pfam_val, smart_val, None, interpro_val))
                        self.domain_type_set.add(regID)
                    aa_s, aa_e = int(feat.location.start), int(feat.location.end)
                    is_splice = self._handle_splice_domains(t_id, p_ref, None, regID, aa_s, aa_e)
                    self.buffers["DomainEvent"].append((p_ref, None, regID, aa_s, aa_e, aa_s*3, aa_e*3, (aa_e-aa_s)*3, "", is_splice, 1))
            self.flush_buffers(force=True)
            self.commit()
            print(f"  Finished processing GPFF. Total records: {counter}. Time elapsed: {time.time() - time_start:.2f} seconds")

    def process_ensembl_domains(self, sp_dir, sp_name):
        print(f"  Processing Ensembl domain annotations for {sp_name}...")
        external_dbs = ["interpro", "pfam", "smart", "tigrfams"]
        PRINT_INTERVAL = 300  # 5 minutes
        self.connect()
        self.cur.execute("BEGIN TRANSACTION;")
        time_start = time.time()
        last_print_time = time_start
        for ext in external_dbs:
            print(f"    Checking for {ext} domain file...")
            f_path = os.path.join(sp_dir, "ensembl", f"{sp_name}.Domains.{ext}.txt")
            if not os.path.exists(f_path): 
                continue
            try: 
                df = pd.read_table(f_path, sep="\t")
            except Exception as e:
                print(f"    Warning: Could not read {f_path} due to error: {e}. Skipping.")
                continue
            df.columns = ['protein_stable_id', 'transcript_stable_id', 'domain_id', 'start', 'end', 'description']
            df.dropna(subset=['protein_stable_id', 'domain_id', 'start', 'end'], inplace=True)
            for counter, row in df.itertuples():
                if counter % 1000 == 0:
                    self.flush_buffers(force=False)
                current_time = time.time()
                if current_time - last_print_time >= PRINT_INTERVAL:
                    print(f"\tStatus Update: Processed {counter} {ext} records. Time: {time.ctime()}")
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
                is_splice = self._handle_splice_domains(t_id, None, p_id, regID, aa_s, aa_e)
                self.buffers["DomainEvent"].append((None, p_id, regID, aa_s, aa_e, aa_s*3, aa_e*3, (aa_e-aa_s)*3, row.id, is_splice, 1))
            print(f"    Finished processing {ext} domains. Total records: {counter}. Time elapsed: {time.time() - time_start:.2f} seconds")
            self.flush_buffers(force=True)
            self.commit()


    # --- PASS 3: Multi-Species Orthology ---
    def process_multi_species_orthology(self, file_path, source_species, gene_symbol_cache):
        if not os.path.exists(file_path): return
        print(f"  Parsing orthology file: {file_path}")
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
                print(f"    Warning: Could not determine species for column '{target_id_col}'. Skipping.")
                continue
            
            # dropna handles the lack of filters in the wget query
            subset = df[[source_col, target_id_col]].dropna()
            for _, row in subset.iterrows():
                total_pairs += 1
                if total_pairs % 10000 == 0:
                    self.flush_buffers(specific_table="Orthology", force=False)
                current_time = time.time()
                if current_time - last_print_time >= PRINT_INTERVAL:
                    print(f"\tStatus Update: Processed {total_pairs} orthology pairs. Time: {time.ctime()}")
                    last_print_time = current_time
                
                source_id = self.clean_id(row[0])
                target_id = self.clean_id(row[1])
                source_symbol = gene_symbol_cache.get(source_id, "")
                target_symbol = gene_symbol_cache.get(target_id, "")
                self.buffers["Orthology"].append((source_id, source_symbol, source_species, target_id, target_symbol, target_species))
            self.flush_buffers(specific_table="Orthology", force=True)
            self.commit()
            print(f"  Finished processing orthology file. Total orthology pairs: {total_pairs}. Time elapsed: {time.time() - time_start:.2f} seconds")


def run_dochap_pipeline(root_dir, db_path, orthology_files=None):
    time_start = time.time()
    # Create the main database with empty tables
    builder = DoChaPBuilder(db_path)
    
    # Collect all species directories
    species_folders = [f for f in os.listdir(root_dir) 
                      if os.path.isdir(os.path.join(root_dir, f))]
    
    print(f"\nFound {len(species_folders)} species to process")
    for species_folder in species_folders:
        sp_path = os.path.join(root_dir, species_folder)
        print(f"\n--- Processing {species_folder} ---")
        for src in ['refseq', 'ensembl']:
            src_dir = os.path.join(sp_path, src)
            if os.path.exists(src_dir):
                gffs = [f for f in os.listdir(src_dir) if f.endswith(('.gff', '.gff3'))]
                if gffs: 
                    builder.process_gff(os.path.join(src_dir, gffs[0]), species_folder, src)
                else:
                    print(f"  No GFF file found for {src} in {species_folder}. Skipping GFF processing.")
        
        ref_dir = os.path.join(sp_path, 'refseq')
        if os.path.exists(ref_dir):
            for gpff in [f for f in os.listdir(ref_dir) if f.endswith(('.gpff', '.gbff'))]:
                builder.process_refseq_proteins(os.path.join(ref_dir, gpff))
        #builder.process_ensembl_domains(sp_path, species_folder)
    
    # Process Orthology files (in main database after all species data is loaded)
    if orthology_files:
        print("\n--- Processing Orthology Tables ---")
        # Build gene symbol cache once for all orthology files
        print("  Building gene symbol cache...")
        gene_symbol_cache = {}
        with sqlite3.connect(builder.db_name) as con:
            cur = con.cursor()
            cur.execute("SELECT gene_ensembl_id, gene_symbol FROM Genes WHERE gene_ensembl_id IS NOT NULL")
            for gene_id, gene_symbol in cur.fetchall():
                gene_symbol_cache[gene_id] = gene_symbol if gene_symbol else ""
        print(f"  Cached {len(gene_symbol_cache)} gene symbols")
        
        # Process orthology using the existing builder (already points to main database)
        for source_species, file_name in orthology_files.items():
            builder.process_multi_species_orthology(file_name, source_species, gene_symbol_cache)
    
    # Create indexes after all data is inserted for optimal performance
    print("\n--- Creating Indexes ---")
    builder.create_index()
    
    elapsed = time.time() - time_start   
    print(f"\n=== PIPELINE COMPLETE ===")
    print(f"Total elapsed time: {elapsed/60:.2f} minutes ({elapsed:.1f} seconds)")
    print(f"Database: {builder.db_name}")

def main():
    """
    Main entry point for DoChaP database builder
    Set max_workers to control parallel processing:
    - max_workers=1: Sequential processing (original behavior)
    - max_workers>1: Process species in parallel (recommended: 4 for typical multi-species datasets)
    """
    # Mapping of source species to their downloaded orthology files
    ortho_data = {
        "H_sapiens": "./genomic_data/human_orthology.txt",
        "M_musculus": "./genomic_data/mouse_orthology.txt",
        "R_norvegicus": "./genomic_data/rat_orthology.txt",
        "D_rerio": "./genomic_data/zebrafish_orthology.txt"
    }
    run_dochap_pipeline("./genomic_data", "DoChaP_Final", ortho_data)

if __name__ == "__main__":
    main()
