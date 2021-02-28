from sqlite3 import connect
import pandas as pd
import numpy as np
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
        self.DomainOrg = DomainOrganizer(download=download)

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
                Domdf = Domdf.fillna(-1)
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
                MainOrtho = MainOrtho.append(merged_df, sort=False)
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

