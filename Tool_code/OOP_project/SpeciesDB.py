from sqlite3 import connect
import pandas
import sys
import os

sys.path.append(os.getcwd())
from Collector import Collector
from DomainOrganizer import DomainOrganizer
from Director import Director
from recordTypes import Protein


class dbBuilder:

    def __init__(self, species, download=False, withEns=True):
        self.species = species
        self.dbName = None
        self.data = Collector(self.species)
        self.data.collectAll(completeMissings=True, download=download, withEns=withEns)
        self.TrnascriptNoProteinRec = {}
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
                                cd TEXT,
                                cl TEXT,
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
                                    H_sapiens_id TEXT,
                                    H_sapiens_name TEXT,
                                    M_musculus_id TEXT,
                                    M_musculus_name TEXT,
                                    R_norvegicus_id TEXT,
                                    R_norvegicus_name TEXT,
                                    D_rerio_id TEXT,
                                    D_rerio_name TEXT,
                                    X_tropicalis_id TEXT,
                                    X_tropicalis_name TEXT,
                                    PRIMARY KEY (H_sapiens_id, M_musculus_id, R_norvegicus_id,\
                                    D_rerio_id, X_tropicalis_id)
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
            prot = set()
            relevantDomains = set()

            for transcript in self.data.Transcripts.values():
                GeneID = str(transcript.gene_GeneID)
                ensGene = transcript.gene_ensembl
                protein_refseq = transcript.protein_refseq
                prot_ens = transcript.protein_ensembl
                if transcript.refseq not in self.data.Genes.keys():
                    self.TrnascriptNoProteinRec[(transcript.refseq, transcript.ensembl,)] = transcript
                    continue
                e_counts = len(transcript.exon_starts)
                # insert into Transcripts table
                if transcript.CDS is None:
                    transcript.CDS = transcript.tx
                values = (transcript.refseq, transcript.ensembl,) + \
                         transcript.tx + transcript.CDS + \
                         (e_counts, GeneID, ensGene, protein_refseq, prot_ens,)
                cur.execute('''INSERT INTO Transcripts
                            (transcript_refseq_id, transcript_ensembl_id, tx_start, tx_end, cds_start,\
                             cds_end, exon_count, gene_GeneID_id, gene_ensembl_id, protein_refseq_id, protein_ensembl_id) 
                            VALUES(?,?,?,?,?,?,?,?,?,?,?)''', values)

                # insert into Genes table (unique GeneID as primary key)
                if GeneID is not geneSet and ensGene not in geneSet:
                    syno = [self.data.Genes[transcript.refseq].synonyms if transcript.refseq is not None else None][0]
                    values = (GeneID, ensGene, transcript.geneSymb,
                              syno, transcript.chrom, transcript.strand, self.species,)
                    cur.execute(''' INSERT INTO Genes
                                (gene_GeneID_id, gene_ensembl_id, gene_symbol, synonyms, chromosome,\
                                 strand, specie)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''', values)
                    geneSet.add(GeneID)
                    geneSet.add(ensGene)

                # insert into Transcript_Exon table
                start_abs, stop_abs = transcript.exons2abs()
                ex_num = 0
                starts = transcript.exon_starts.copy()
                ends = transcript.exon_ends.copy()
                if transcript.strand == '-':
                    starts = starts[::-1]
                    ends = ends[::-1]
                for iEx in range(e_counts):
                    ex_num += 1
                    values = (transcript.refseq, transcript.ensembl, ex_num, starts[iEx], ends[iEx],
                              start_abs[iEx], stop_abs[iEx],)
                    cur.execute(''' INSERT INTO Transcript_Exon
                                (transcript_refseq_id, transcript_ensembl_id, order_in_transcript,\
                                genomic_start_tx, genomic_end_tx, abs_start_CDS, abs_end_CDS)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''', values)

                    # insert into Exons table
                    values = (GeneID, ensGene, starts[iEx], ends[iEx],)
                    if values not in uExon:
                        uExon.add(values)
                        cur.execute('''INSERT INTO Exons
                                    (gene_GeneID_id, gene_ensembl_id, genomic_start_tx, genomic_end_tx)
                                    VALUES (?, ?, ?, ?)''', values)

                # insert into Proteins table
                protID = [protein_refseq if protein_refseq is not None or '-' else None][0]
                protein = self.data.Proteins[protID]
                values = (protein.refseq, prot_ens, protein.description, protein.length,
                          protein.note, transcript.refseq, transcript.ensembl,)
                cur.execute(''' INSERT INTO Proteins
                                (protein_refseq_id, protein_ensembl_id, description, length, synonyms, transcript_refseq_id, transcript_ensembl_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''', values)
                if protID in self.data.Domains.keys():
                    splicin = set()
                    for reg in self.data.Domains[protID]:
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
                        values = (protein_refseq, prot_ens, regID,
                                  reg.aaStart, reg.aaEnd, reg.nucStart, reg.nucEnd, total_length,
                                  reg.extID, splice_junction, complete,)
                        if values not in domeve:
                            cur.execute(''' INSERT INTO DomainEvent
                                        (protein_refseq_id, protein_ensembl_id, type_id,\
                                        AA_start, AA_end, nuc_start, nuc_end, total_length,\
                                        ext_id, splice_junction, complete_exon)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
                            domeve.add(values)

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
                                    cd TEXT,
                                    cl TEXT,
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
                                    (type_id, name, other_name, description, CDD_id, cd, cl,\
                                    pfam, smart, tigr, interpro)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
        con.commit()

    def AddOrthology(self, Orthology_df):
        with connect(self.dbName + '.sqlite') as con:
            Orthology_df.to_sql("Orthology", con, if_exists="replace")
