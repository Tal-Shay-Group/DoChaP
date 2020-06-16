from sqlite3 import connect
import pandas as pd
import sys
import os
import time

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
        self.DomainOrg = DomainOrganizer()

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
                                gene_GeneID_id TEXT,
                                gene_ensembl_id TEXT,
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
                                transcript_refseq_id TEXT,
                                transcript_ensembl_id TEXT,
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
                                protein_refseq_id TEXT,
                                protein_ensembl_id TEXT,
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
                                PRIMARY KEY(protein_refseq_id, protein_ensembl_id, type_id, AA_start, total_length, ext_id),
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
                                    A_Species TEXT,
                                    B_ensembl_id TEXT,
                                    B_GeneSymb TEXT,
                                    B_Species TEXT,
                                    PRIMARY KEY (A_ensembl_id, B_ensembl_id),
                                    FOREIGN KEY (A_ensembl_id, B_ensembl_id, A_GeneSymb, B_GeneSymb, A_Species, B_Species) 
                                    REFERENCES Genes(gene_ensembl_id, gene_ensembl_id, gene_symbol, gene_symbol, specie, specie)
                                    );"""
                            )

    def create_index(self):
        with connect(self.dbName + '.sqlite') as con:
            cur = con.cursor()
            cur.execute('''CREATE INDEX geneTableIndexBySpecies ON Genes(specie);''')
            cur.execute('''CREATE INDEX transcriptTableIndexByGene ON Transcripts(gene_GeneID_id) ;''')
            cur.execute(
                '''CREATE INDEX exonsInTranscriptsTableIndexByTranscripts ON Transcript_Exon(transcript_refseq_id) ;''')
            cur.execute('''CREATE INDEX domainEventsTableIndexByProtein ON DomainEvent(protein_refseq_id) ;''')
            cur.execute('''CREATE INDEX domainEventsTableIndexByEnsembl ON DomainEvent(protein_ensembl_id);''')
            cur.execute(
                '''CREATE INDEX exonInTranscriptsTableIndexByEnsembl ON Transcript_Exon(transcript_ensembl_id);''')

    def fill_in_db(self, CollectDomainsFromMerged=True, merged=True, dbName=None):
        """
        This function in for unique species. for more than ine use add Species To Merged
        """
        if dbName is not None:
            self.dbName = dbName
        elif merged:
            self.dbName = 'DB_merged'
        else:
            self.dbName = 'DB_' + self.species
        if CollectDomainsFromMerged:
            self.DomainOrg.collectDatafromDB(self.DomainsSourceDB)

        with connect(self.dbName + '.sqlite') as con:
            print("Connected to " + self.dbName + "...")
            print("Filling in the tables...")
            cur = con.cursor()
            geneSet = set()
            uExon = set()
            domeve = set()
            relevantDomains = set()

            for tID, transcript in self.data.Transcripts.items():
                ensemblkey = False
                if tID.startswith("ENS"):
                    ensemblkey = True
                e_counts = len(transcript.exon_starts)
                # insert into Transcripts table
                if transcript.CDS is None:
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
                    if ensemblkey:
                        gene = self.data.Genes[transcript.gene_ensembl]
                        # syno = gene.synonyms
                    else:
                        gene = self.data.Genes[transcript.gene_GeneID]
                        # syno = [self.data.Genes[transcript.gene_GeneID].synonyms
                        #       if transcript.gene_GeneID is not None else None][0]
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
                    values = (protein.refseq, protein.ensembl, regID,
                              reg.aaStart, reg.aaEnd, reg.nucStart, reg.nucEnd, total_length,
                              reg.extID, splice_junction, complete,)
                    if values not in domeve:
                        cur.execute(''' INSERT INTO DomainEvent
                                    (protein_refseq_id, protein_ensembl_id, type_id,\
                                    AA_start, AA_end, nuc_start, nuc_end, total_length,\
                                    ext_id, splice_junction, complete_exon)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
                        domeve.add(values)
            bp = time.time()
            if merged:
                relevantDomains = set(self.DomainOrg.allDomains.keys())
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
            for typeID in relevantDomains:
                if typeID in self.DomainOrg.allDomains.keys():
                    values = (typeID,) + self.DomainOrg.allDomains[typeID]
                    cur.execute(''' INSERT INTO DomainType
                                    (type_id, name, other_name, description, CDD_id, cdd,\
                                    pfam, smart, tigr, interpro)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
            print("#### Filling in domain type table: %s seconds" % (time.time() - bp))
        con.commit()

    def AddOrthology(self, orthologsDict):
        MainOrtho = pd.DataFrame(columns=['A_ensembl_id', 'A_GeneSymb', 'A_Species',
                                          'B_ensembl_id', 'B_GeneSymb', 'B_Species'])
        db_data = dict()
        species = [spec for x in orthologsDict.keys() for spec in x]
        with connect(self.dbName + '.sqlite') as con:
            for spec in species:
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
            MainOrtho = MainOrtho.append(merged_df, sort=False)
        print("Filling in Orthology table...")
        MainOrtho.to_sql("Orthology", con, if_exists="append", index=False)
        print("Filling Orthology table complete!")

    # def AddTableToMerged(self, db2add):
    #     db_a = connect(self.dbName + '.sqlite')
    #     db_b_name = db2add
    #     a_c = db_a.cursor()
    #     a_c.execute('''ATTACH ? AS db_b''', (db_b_name,))
    #     a_c.execute('''INSERT INTO Exons SELECT * FROM db_b.Exons''')
    #     a_c.execute('''INSERT INTO Transcripts SELECT * FROM db_b.Transcripts''')
    #     a_c.execute('''INSERT INTO Transcript_Exon SELECT * FROM db_b.Transcript_Exon''')
    #     a_c.execute('''INSERT INTO Genes SELECT * FROM db_b.Genes''')
    #     a_c.execute('''INSERT INTO Proteins SELECT * FROM db_b.Proteins''')
    #     db_a.commit()
