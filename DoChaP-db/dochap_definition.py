import sqlite3
import time
import pandas as pd

class DoChaPDB:
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

    
    def create_transcript_exon_table(self):
        self.cur.executescript("DROP TABLE IF EXISTS Transcript_Exon;")
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

