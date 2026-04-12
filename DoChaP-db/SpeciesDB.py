from concurrent.futures import process
from sqlite3 import connect
import pandas as pd
import numpy as np
import sys
import os
import time

import psutil

sys.path.append(os.getcwd())
from Collector import Collector
from DomainOrganizer import DomainOrganizer
# from DomainOrganizer import DomainOrganizerPD
from recordTypes import Protein


class dbBuilder:

    def __init__(self, species, download=False, withEns=True):
        self.species = species
        self.dbName = None
        self.data = Collector(self.species)
        self.data.collectAll(download=download, withEns=withEns)
        self.TranscriptNoProteinRec = {}
        self.DomainsSourceDB = 'DB_merged.sqlite'
        self.DomainOrg = DomainOrganizer(download=False)

    def create_tables_db(self, merged=True, dbName=None):
        """
        Create a transcripts table in the specie database and fills with ucsc transcripts data
        """
        if dbName is not None:
            self.dbName = dbName
        elif merged:
            self.dbName = 'DB_merged'
        else:
            self.dbName = 'DB_' + self.species

        print("Creating database: {}...".format(self.dbName))
        with connect(self.dbName + '.sqlite') as con:
            cur = con.cursor()
            cur.executescript('DROP TABLE IF EXISTS Genes;')
            print('Creating the table: Genes')
            cur.execute('''
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
            cur.executescript("DROP TABLE IF EXISTS transcripts;")
            print('Creating the table: Transcripts')
            cur.execute('''
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
                                FOREIGN KEY(gene_GeneID_id, gene_ensembl_id) REFERENCES Genes(gene_GeneID_id, gene_ensembl_id),
                                FOREIGN KEY(protein_refseq_id,protein_ensembl_id) REFERENCES Proteins(protein_refseq_id,protein_ensembl_id)
                                );'''
                        )
            cur.executescript("DROP TABLE IF EXISTS Exons;")
            print('Creating the table: Exons')
            cur.execute('''
                        CREATE TABLE Exons(
                                gene_GeneID_id TEXT,
                                gene_ensembl_id TEXT,        
                                genomic_start_tx INTEGER,
                                genomic_end_tx INTEGER,
                                PRIMARY KEY (gene_GeneID_id, gene_ensembl_id, genomic_start_tx, genomic_end_tx),
                                FOREIGN KEY(gene_GeneID_id, gene_ensembl_id) REFERENCES Genes(gene_GeneID_id, gene_ensembl_id)
                                );'''
                        )

            cur.executescript("DROP TABLE IF EXISTS Transcript_Exon;")
            print('Creating the table: Transcript_Exon')
            cur.execute('''
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
                                 REFERENCES Transcripts(transcript_refseq_id, transcript_ensembl_id),
                                FOREIGN KEY(genomic_start_tx, genomic_end_tx)\
                                 REFERENCES Exons(genomic_start_tx, genomic_end_tx)
                                );'''
                        )

            cur.executescript("DROP TABLE IF EXISTS Proteins;")
            print('Creating the table: Proteins')
            cur.execute('''
                        CREATE TABLE Proteins(
                                protein_refseq_id TEXT UNIQUE,
                                protein_ensembl_id TEXT UNIQUE,
                                description TEXT,
                                synonyms TEXT,
                                length INTEGER,
                                transcript_refseq_id TEXT,
                                transcript_ensembl_id TEXT,
                                PRIMARY KEY(protein_refseq_id, protein_ensembl_id),
                                FOREIGN KEY(transcript_refseq_id, transcript_ensembl_id) REFERENCES Transcripts(transcript_refseq_id, transcript_ensembl_id)
                                );'''
                        )
            cur.executescript("DROP TABLE IF EXISTS DomainType;")
            print('Creating the table: DomainType')
            cur.execute('''
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
            cur.executescript("DROP TABLE IF EXISTS DomainEvent;")
            print('Creating the table: DomainEvent')
            cur.execute('''
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
            cur.executescript("DROP TABLE IF EXISTS SpliceInDomains;")
            print('Creating the table: SpliceInDomains')
            cur.execute("""
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
                                FOREIGN KEY(exon_order_in_transcript) REFERENCES Transcript_Exon(order_in_transcript),
                                FOREIGN KEY(type_id) REFERENCES DomainType(type_id),
                                FOREIGN KEY(domain_nuc_start, total_length) REFERENCES DomainEvent(Nuc_start, total_length)
                                );"""
                        )
            if merged:
                cur.executescript("DROP TABLE IF EXISTS Orthology;")
                print('Creating the table: Orthology')
                cur.execute("""
                            CREATE TABLE Orthology(
                                    A_ensembl_id TEXT,
                                    A_GeneSymb TEXT,
                                    A_species TEXT,
                                    B_ensembl_id TEXT,
                                    B_GeneSymb TEXT,
                                    B_species TEXT,
                                    PRIMARY KEY (A_ensembl_id, B_ensembl_id),
                                    FOREIGN KEY (A_ensembl_id, B_ensembl_id, A_GeneSymb, B_GeneSymb, A_species, B_species) 
                                    REFERENCES Genes(gene_ensembl_id, gene_ensembl_id, gene_symbol, gene_symbol, specie, specie)
                                    );"""
                            )
        # ~~~ disconnect database ~~~

    def create_index(self):
        """ Creates index for for efficient searches"""
        with connect(self.dbName + '.sqlite') as con:
            cur = con.cursor()
            cur.execute('''CREATE INDEX IF NOT EXISTS geneTableIndexBySpecies ON Genes(specie);''')
            cur.execute('''CREATE INDEX IF NOT EXISTS transcriptTableIndexByGene ON Transcripts(gene_GeneID_id) ;''')
            cur.execute(
                '''CREATE INDEX IF NOT EXISTS exonsInTranscriptsTableIndexByTranscripts ON Transcript_Exon(transcript_refseq_id) ;''')
            cur.execute('''CREATE INDEX IF NOT EXISTS domainEventsTableIndexByProtein ON DomainEvent(protein_refseq_id) ;''')
            cur.execute('''CREATE INDEX IF NOT EXISTS domainEventsTableIndexByEnsembl ON DomainEvent(protein_ensembl_id);''')
            cur.execute(
                '''CREATE INDEX IF NOT EXISTS exonInTranscriptsTableIndexByEnsembl ON Transcript_Exon(transcript_ensembl_id);''')
            con.commit()
            cur.execute("ANALYZE")
            con.commit()    

    def get_memory_usage(self):
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 ** 3)  # Convert bytes to GB

    def flush_buffers(self, cur, buffers, force=False, specific=None, BATCH_SIZE=5000):
        """Helper to write lists to DB and clear them"""
        queries = {
            "Transcripts": "INSERT OR IGNORE INTO Transcripts (transcript_refseq_id, transcript_ensembl_id, tx_start, tx_end, cds_start, cds_end, exon_count, gene_GeneID_id, gene_ensembl_id, protein_refseq_id, protein_ensembl_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            "Genes": "INSERT OR IGNORE INTO Genes (gene_GeneID_id, gene_ensembl_id, gene_symbol, synonyms, chromosome, strand, specie) VALUES (?, ?, ?, ?, ?, ?, ?)",
            "Transcript_Exon": "INSERT OR IGNORE INTO Transcript_Exon (transcript_refseq_id, transcript_ensembl_id, order_in_transcript, genomic_start_tx, genomic_end_tx, abs_start_CDS, abs_end_CDS) VALUES (?, ?, ?, ?, ?, ?, ?)",
            "Exons": "INSERT OR IGNORE INTO Exons (gene_GeneID_id, gene_ensembl_id, genomic_start_tx, genomic_end_tx) VALUES (?, ?, ?, ?)",
            "Proteins": "INSERT OR IGNORE INTO Proteins (protein_refseq_id, protein_ensembl_id, description, length, synonyms, transcript_refseq_id, transcript_ensembl_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            "SpliceInDomains": "INSERT OR IGNORE INTO SpliceInDomains (transcript_refseq_id, transcript_ensembl_id, exon_order_in_transcript, domain_nuc_start, type_id, total_length, included_len, exon_num_in_domain) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            "DomainEvent": "INSERT OR IGNORE INTO DomainEvent (protein_refseq_id, protein_ensembl_id, type_id, AA_start, AA_end, nuc_start, nuc_end, total_length, ext_id, splice_junction, complete_exon) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            "DomainType": "INSERT INTO DomainType (type_id, name, other_name, description, CDD_id, cdd, pfam, smart, tigr, interpro) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        }
        if specific:
            table = specific
            data = buffers[table]
            if len(data) >= BATCH_SIZE or (force and data):
                cur.executemany(queries[table], data)
                buffers[table] = []
        else:
            for table, data in buffers.items():
                if len(data) >= BATCH_SIZE or (force and data):
                    cur.executemany(queries[table], data)
                    buffers[table] = []

    def fill_in_db(self, CollectDomainsFromMerged=True, merged=True, dbName=None):
        """
        This is filling the database with the collected data for a single species.
        if used db is "merged" than set True to the param. if False than a species unique db will be created.
        """
        if dbName is not None:
            self.dbName = dbName
        elif merged:
            self.dbName = 'DB_merged'
        else:
            self.dbName = 'DB_' + self.species
        if CollectDomainsFromMerged:  # to keep domain ids consistent between the merged & single species db
            self.DomainOrg.collectDatafromDB(self.DomainsSourceDB)
            preDomains = set(self.DomainOrg.allDomains.keys())
        
        with connect(self.dbName + '.sqlite') as con:
            print(f"Connected to {self.dbName}...")
            print("Filling in the tables with bulk inserts...")
            cur = con.cursor()
            cur.execute("PRAGMA journal_mode = MEMORY;") # Keep undo-logs in RAM, not disk
            cur.execute("PRAGMA synchronous = OFF;")    # Don't wait for disk confirmation
            cur.execute("PRAGMA cache_size = 100000;")  # Give SQLite 100MB of RAM for index caching
            cur.execute("PRAGMA temp_store = MEMORY;")   # Use RAM for temporary tables/sorting
            cur.execute("BEGIN TRANSACTION;")
            # Configuration
            BATCH_SIZE = 5000
            
            # Accumulators
            buffers = {
                "Transcripts": [], "Genes": [], "Transcript_Exon": [],
                "Exons": [], "Proteins": [], "SpliceInDomains": [], "DomainEvent": [], "DomainType": []
            }
            
            geneSet = set()
            uExon = set()
            relevantDomains = set()

            print("Processing transcripts: {}".format(len(self.data.Transcripts)))
            count = 0
            bp = time.time()
            for tID, transcript in self.data.Transcripts.items():
                count += 1
                if count % 5000 == 0:
                    now = time.time()
                    elapsed = now - bp # Uses the 'bp' start time you defined earlier
                    tps = count / elapsed if elapsed > 0 else 0
                    print(f"[{count}] Speed: {tps:.2f} t/s | RAM: {self.get_memory_usage():.2f} GB")
                    print(f"\t--- uExon: {len(uExon)} items | geneSet: {len(geneSet)} items")
                    self.flush_buffers(cur, buffers, force=False)
                    print(f"\t--- RAM after flush: {self.get_memory_usage():.2f} GB")
                gID = transcript.gene_GeneID
                ensemblkey = tID.startswith("ENS")
                e_counts = len(transcript.exon_starts)

                # 1. Transcripts Buffer
                if transcript.CDS is None:
                    print("Transcript {} from {} has None in CDS".format(tID, self.species))
                    transcript.CDS = transcript.tx
                
                buffers["Transcripts"].append(
                    (transcript.refseq, transcript.ensembl) + transcript.tx + transcript.CDS + 
                    (e_counts, gID, transcript.gene_ensembl, 
                    transcript.protein_refseq, transcript.protein_ensembl)
                )

                # 2. Genes Buffer
                gID_hash = hash(gID) if gID else None
                ensID_hash = hash(transcript.gene_ensembl) if transcript.gene_ensembl else None
                if gID_hash not in geneSet and ensID_hash not in geneSet:
                    gene = self.data.Genes.get(gID or transcript.gene_ensembl, 
                                            self.data.Genes.get(transcript.gene_ensembl))
                    if gene is None:
                        raise ValueError(f"No gene found for {tID}")
                    
                    buffers["Genes"].append((gene.GeneID, gene.ensembl, gene.symbol, gene.synonyms, 
                                            gene.chromosome, gene.strand, self.species))
                    if gID_hash: 
                        geneSet.add(gID_hash)
                    if ensID_hash: 
                        geneSet.add(ensID_hash)
                    

                # 3. Exons Buffers
                start_abs, stop_abs = transcript.exons2abs()
                #starts, ends = transcript.exon_starts, transcript.exon_ends
                starts = transcript.exon_starts.copy()
                ends = transcript.exon_ends.copy()
                for i in range(e_counts):
                    # Transcript_Exon
                    buffers["Transcript_Exon"].append((transcript.refseq, transcript.ensembl, i+1, 
                                                    starts[i], ends[i], start_abs[i], stop_abs[i]))
                    # Unique Exons
                    ex_val = (gID, transcript.gene_ensembl, starts[i], ends[i])
                    hash_val = hash(ex_val) # use hash to avoid storing large exon tuples in memory for the set, but still ensure uniqueness
                    if hash_val not in uExon:
                        uExon.add(hash_val)
                        buffers["Exons"].append(ex_val)

                # 4. Proteins Buffer
                protID = transcript.protein_ensembl if ensemblkey else transcript.protein_refseq
                protein = self.data.Proteins[protID]
                buffers["Proteins"].append((protein.refseq, protein.ensembl, protein.description, 
                                            protein.length, protein.synonyms, transcript.refseq, transcript.ensembl))

                # 5. Domains (Keep using DataFrame for logic, but move SpliceIn to buffer)
                temp_dom_events = []
                splicin_local = set()
                temp_rows = []
                for reg in self.data.Domains.get(protID, [None]):
                    if reg is None: continue
                    regID = self.DomainOrg.addDomain(reg)
                    if regID is None: continue
                    
                    relevantDomains.add(regID)
                    relation, exon_list, length = reg.domain_exon_relationship(start_abs, stop_abs)
                    total_length = reg.nucEnd - reg.nucStart + 1
                    
                    splice_junction = 1 if relation == 'splice_junction' else 0
                    complete = 1 if relation == 'complete_exon' else 0
                    
                    if splice_junction:
                        for j in range(len(exon_list)):
                            s_val = (transcript.refseq, transcript.ensembl, exon_list[j], 
                                    reg.nucStart, regID, total_length, length[j], j + 1)
                            if s_val not in splicin_local:
                                buffers["SpliceInDomains"].append(s_val)
                                splicin_local.add(s_val)

                    extWithInter = "; ".join(filter(None, [reg.extID, self.DomainOrg.allDomains[regID][-1]]))
                    # Collect as a simple tuple instead of a DataFrame row
                    temp_rows.append((
                        protein.refseq, protein.ensembl, regID,
                        reg.aaStart, reg.aaEnd, reg.nucStart, reg.nucEnd, total_length,
                        extWithInter, splice_junction, complete
                    ))
                    

                # Process DomainEvent via Pandas
                if temp_rows:
                    # Grouping by all columns except ext_id (index 8)
                    grouped = {}
                    for row in temp_rows:
                        key = row[:8] + row[9:] # All except ext_id
                        ext_id = row[8]
                        if key not in grouped:
                            grouped[key] = set()
                        grouped[key].add(str(ext_id))
                    
                    for key, ext_ids in grouped.items():
                        final_ext_id = "; ".join(ext_ids)
                        # Reconstruct full row: key[0:8] is first 8 cols, key[8:] is last 2
                        final_row = key[:8] + (final_ext_id,) + key[8:]
                        buffers["DomainEvent"].append(final_row)
               

            # Final flush for remaining records
            self.flush_buffers(cur, buffers, force=True)
            con.commit()
            bp = time.time()

            if merged:
                relevantDomains = preDomains.union(relevantDomains)
                print('Recreating the table: DomainType and update domains')
                cur.executescript("DROP TABLE IF EXISTS DomainType;")
                print('Creating the table: DomainType')
                cur.execute('''
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
            # insert into domain type table
            postDomains = set(self.DomainOrg.allDomains.keys())
            print("from all {} domains in organizer, {} not in relevant domains".format(len(postDomains),
                                                                                        len(postDomains.difference(relevantDomains))))
            cur.execute("BEGIN TRANSACTION;")
            count = 0
            for typeID in relevantDomains:
                count += 1
                if count % 5000 == 0:
                    elapsed = time.time() - bp 
                    tps = count / elapsed if elapsed > 0 else 0
                    print(f"Processed {count} domains... Speed: {tps:.2f} domains/sec")
                    self.flush_buffers(cur, buffers, specific="DomainType")
                if typeID in self.DomainOrg.allDomains.keys():
                    values = (typeID,) + self.DomainOrg.allDomains[typeID]
                    buffers["DomainType"].append(values)
            self.flush_buffers(cur, buffers, specific="DomainType", force=True)
            con.commit() # Final commit for DomainType
            print("#### Filling in domain type table: %s seconds" % (time.time() - bp))


    def fill_in_db_org(self, CollectDomainsFromMerged=True, merged=True, dbName=None):
        """
        This is filling the database with the collected data for a single species.
        if used db is "merged" than set True to the param. if False than a species unique db will be created.
        """
        if dbName is not None:
            self.dbName = dbName
        elif merged:
            self.dbName = 'DB_merged'
        else:
            self.dbName = 'DB_' + self.species
        if CollectDomainsFromMerged:  # to keep domain ids consistent between the merged & single species db
            self.DomainOrg.collectDatafromDB(self.DomainsSourceDB)
            preDomains = set(self.DomainOrg.allDomains.keys())

        with connect(self.dbName + '.sqlite') as con:
            print("Connected to " + self.dbName + "...")
            print("Filling in the tables...")
            cur = con.cursor()
            geneSet = set()
            uExon = set()
            relevantDomains = set()

            for tID, transcript in self.data.Transcripts.items():
                ensemblkey = False
                if tID.startswith("ENS"):
                    ensemblkey = True
                e_counts = len(transcript.exon_starts)
                # insert into Transcripts table
                if transcript.CDS is None:
                    print("Transcript {} from {} has None in CDS".format(tID, self.species))
                    transcript.CDS = transcript.tx
                values = (transcript.refseq, transcript.ensembl,) + transcript.tx + transcript.CDS + \
                         (e_counts, transcript.gene_GeneID, transcript.gene_ensembl,
                          transcript.protein_refseq, transcript.protein_ensembl,)
                cur.execute('''INSERT INTO Transcripts
                            (transcript_refseq_id, transcript_ensembl_id, tx_start, tx_end, cds_start,\
                             cds_end, exon_count, gene_GeneID_id, gene_ensembl_id, protein_refseq_id, protein_ensembl_id) 
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)''', values)

                # insert into Genes table
                if transcript.gene_GeneID not in geneSet and \
                        transcript.gene_ensembl not in geneSet:
                    gene = self.data.Genes.get(
                        transcript.gene_GeneID if transcript.gene_GeneID is not None else transcript.gene_ensembl,
                        self.data.Genes.get(transcript.gene_ensembl, None))
                    if gene is None:
                        raise ValueError("No gene in Genes for transcript {}, {}. GeneID: {}, ensembl gene: {}".format(
                            transcript.refseq, transcript.ensembl, transcript.gene_GeneID, transcript.gene_ensembl))
                    # if ensemblkey:
                    #     gene = self.data.Genes.get(transcript.gene_ensembl, self.data.Genes[transcript.gene_GeneID])
                    #     # syno = gene.synonyms
                    # else:
                    #     gene = self.data.Genes[transcript.gene_GeneID]
                    #     # syno = [self.data.Genes[transcript.gene_GeneID].synonyms
                    #     #       if transcript.gene_GeneID is not None else None][0]
                    values = (gene.GeneID, gene.ensembl, gene.symbol,
                              gene.synonyms, gene.chromosome, gene.strand, self.species,)
                    cur.execute(''' INSERT INTO Genes
                                (gene_GeneID_id, gene_ensembl_id, gene_symbol, synonyms, chromosome,\
                                 strand, specie)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''', values)
                    geneSet.add(gene.GeneID)
                    geneSet.add(gene.ensembl)
                    geneSet = geneSet - {None}

                start_abs, stop_abs = transcript.exons2abs()
                ex_num = 0
                starts = transcript.exon_starts.copy()
                ends = transcript.exon_ends.copy()
                for iEx in range(e_counts):
                    ex_num += 1
                    # insert into Transcript_Exon table
                    values = (transcript.refseq, transcript.ensembl, ex_num, starts[iEx], ends[iEx],
                              start_abs[iEx], stop_abs[iEx],)
                    cur.execute(''' INSERT INTO Transcript_Exon
                                (transcript_refseq_id, transcript_ensembl_id, order_in_transcript,\
                                genomic_start_tx, genomic_end_tx, abs_start_CDS, abs_end_CDS)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''', values)

                    # insert into Exons table
                    values = (transcript.gene_GeneID, transcript.gene_ensembl, starts[iEx], ends[iEx],)
                    if values not in uExon:
                        uExon.add(values)
                        cur.execute('''INSERT INTO Exons
                                    (gene_GeneID_id, gene_ensembl_id, genomic_start_tx, genomic_end_tx)
                                    VALUES (?, ?, ?, ?)''', values)

                # insert into Proteins table
                if ensemblkey:
                    protID = transcript.protein_ensembl
                else:
                    protID = transcript.protein_refseq
                protein = self.data.Proteins[protID]
                values = (protein.refseq, protein.ensembl, protein.description, protein.length,
                          protein.synonyms, transcript.refseq, transcript.ensembl,)
                cur.execute(''' INSERT INTO Proteins
                                (protein_refseq_id, protein_ensembl_id, description, length, synonyms, transcript_refseq_id, transcript_ensembl_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''', values)
                splicin = set()
                # domeve = set()
                Domdf = pd.DataFrame(columns=["protein_refseq_id", "protein_ensembl_id", "type_id",
                                              "AA_start", "AA_end", "nuc_start", "nuc_end", "total_length",
                                              "ext_id", "splice_junction", "complete_exon"])
                for reg in self.data.Domains.get(protID, [None]):
                    if reg is None:
                        continue
                    regID = self.DomainOrg.addDomain(reg)
                    if regID is None:
                        continue
                    relevantDomains.add(regID)
                    relation, exon_list, length = reg.domain_exon_relationship(start_abs, stop_abs)
                    total_length = reg.nucEnd - reg.nucStart + 1  # adding one because coordinates are full-closed!
                    splice_junction = 0
                    complete = 0
                    if relation == 'splice_junction':
                        splice_junction = 1
                        for i in range(len(exon_list)):
                            values = (transcript.refseq, transcript.ensembl,
                                      exon_list[i], reg.nucStart, regID,
                                      total_length, length[i], i + 1,)
                            if values not in splicin:
                                cur.execute(''' INSERT INTO SpliceInDomains
                                    (transcript_refseq_id, transcript_ensembl_id,\
                                     exon_order_in_transcript, domain_nuc_start, type_id,\
                                     total_length, included_len, exon_num_in_domain)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', values)
                                splicin.add(values)
                    elif relation == 'complete_exon':
                        complete = 1
                    # insert into domain event table
                    ldf = Domdf.shape[0]
                    extWithInter = "; ".join([reg.extID, self.DomainOrg.allDomains[regID][-1]]) if \
                        self.DomainOrg.allDomains[regID][-1] is not None else reg.extID
                    values = (protein.refseq, protein.ensembl, regID,
                              reg.aaStart, reg.aaEnd, reg.nucStart, reg.nucEnd, total_length,
                              extWithInter, splice_junction, complete,)
                    Domdf.loc[ldf] = list(values)
                Domdf = Domdf.drop_duplicates()
                Domdf.fillna(-1).infer_objects(copy=False)
                Domdf = Domdf.groupby(["protein_refseq_id", "protein_ensembl_id", "type_id",
                                       "AA_start", "AA_end", "nuc_start", "nuc_end", "total_length",
                                       "splice_junction", "complete_exon"],
                                      as_index=False, sort=False).agg(
                    lambda col: "; ".join(set(col)))  # groupby all besides ext_ID
                Domdf = Domdf.replace(-1, np.nan)
                Domdf.to_sql("DomainEvent", con, if_exists="append", index=False)
            # ~~~ end of loop iterating over transcripts ~~~
            bp = time.time()

            if merged:
                relevantDomains = preDomains.union(relevantDomains)
                print('Recreating the table: DomainType and update domains')
                cur.executescript("DROP TABLE IF EXISTS DomainType;")
                print('Creating the table: DomainType')
                cur.execute('''
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
            # insert into domain type table
            postDomains = set(self.DomainOrg.allDomains.keys())
            print("from all {} domains in organizer, {} not in relevant domains".format(len(postDomains),
                                                                                        len(postDomains.difference(relevantDomains))))
            for typeID in relevantDomains:
                if typeID in self.DomainOrg.allDomains.keys():
                    values = (typeID,) + self.DomainOrg.allDomains[typeID]
                    cur.execute(''' INSERT INTO DomainType
                                    (type_id, name, other_name, description, CDD_id, cdd,\
                                    pfam, smart, tigr, interpro)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
            print("#### Filling in domain type table: %s seconds" % (time.time() - bp))

            con.commit()
        # ~~~ disconnect database ~~~

    def AddOrthology(self, orthologsDict):
        """
        This function adds the orthology data to the database, only for the genes included in the database.
        Changes the database with no returned output.
        @param orthologsDict: created by OrthologsBuilder module, called by the main script.
        @return: None
        """
        MainOrtho = pd.DataFrame(columns=['A_ensembl_id', 'A_GeneSymb', 'A_species',
                                          'B_ensembl_id', 'B_GeneSymb', 'B_species'])
        db_data = dict()
        orthology_species = set([spec for x in orthologsDict.keys() for spec in x])
        with connect(self.dbName + '.sqlite') as con:
            cur = con.cursor()
            schema = cur.execute("PRAGMA table_info('Orthology')").fetchall()
            for spec in orthology_species:
                db_data[spec] = pd.read_sql(
                    "SELECT gene_ensembl_id,gene_symbol,specie FROM Genes WHERE specie='{}'".format(spec),
                    con)
            print("collecting orthology data for:")
            for couple, ortho in orthologsDict.items():
                print("\t{} and {}".format(couple[0], couple[1]))
                merged_df = None
                n = 0
                for spec in couple:
                    db_data[spec]['gene_symbol'] = db_data[spec]['gene_symbol'].str.upper()
                    db_data[spec].columns = db_data[spec].columns.str.replace('gene_ensembl_id', spec + "_ID")
                    if n == 0:
                        merged_df = pd.merge(db_data[spec], ortho)
                    else:
                        merged_df = pd.merge(db_data[spec], merged_df)
                    label = 'A' if n == 0 else 'B'
                    merged_df.columns = merged_df.columns.str.replace("specie", label + "_Species")
                    merged_df.columns = merged_df.columns.str.replace("gene_symbol", label + "_GeneSymb")
                    merged_df.columns = merged_df.columns.str.replace(spec + "_ID", label + "_ensembl_id")
                    merged_df = merged_df.drop(spec + "_name", axis=1)
                    n += 1
                merged_df = merged_df.rename(columns={'A_Species': 'A_species', 'B_Species': 'B_species'})
                MainOrtho = pd.concat([MainOrtho, merged_df], axis=0, sort=False, ignore_index=True)
            MainOrtho = MainOrtho.drop_duplicates()
            MainOrtho = MainOrtho.groupby(["A_ensembl_id", "B_ensembl_id"], as_index=False, sort=False).agg(
                lambda col: ', '.join(set(col)))
            print("Filling in Orthology table...")
            try:
                MainOrtho.to_sql("Orthology", con, if_exists="replace", schema=schema, index=False)
            except Exception as err:
                print(err)
                MainOrtho.to_csv("OrthologyTable.Failed.csv")
            print("Filling Orthology table complete!")
        # ~~~ disconnect database ~~~

