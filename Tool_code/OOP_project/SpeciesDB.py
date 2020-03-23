from sqlite3 import connect
import Tool_code.ucscParser

#from Tool_code import ffParser, ffDownloader, order_domains
from OOP_project.Collector import Collector


class dbBuilder:

    def __init__(self, species, merged=True, dbName=None):
        self.merged = merged
        if not self.merged:
            if type(species) is not str:
                raise ValueError('When merged == False, species expects single species provided as str value.')
            self.species = species
            self.dbName = 'DB_' + species
        elif self.merged:
            if type(species) not in [list, tuple, set]:
                raise ValueError(
                    'When building a merged database, species expects list/tuple/set of species to include.')
            self.species = species
            self.dbName = 'DB_merged'
        if dbName is not None:
            self.dbName = dbName
        self.AllDomains = None

    def create_tables_db(self):
        """
        Create a transcripts table in the specie database and fills with ucsc transcripts data
        """

        print("Creating database: {}...".format(self.dbName))
        with connect(self.dbName + '.sqlite') as con:
            cur = con.cursor()
            cur.executescript('DROP TABLE IF EXISTS Genes;')
            print('Creating the table: Genes')
            cur.execute('''
                        CREATE TABLE Genes(
                                gene_refseq_id TEXT,
                                gene_ensembl_id TEXT,
                                gene_symbol TEXT,
                                synonyms TEXT,
                                chromosome TEXT,
                                strand TEXT,
                                specie TEXT, 
                                PRIMARY KEY(gene_refseq_id, gene_ensembl_id, gene_symbol)
                                );'''
                        )
            cur.executescript("DROP TABLE IF EXISTS transcripts;")
            print('Creating the table: Transcripts')
            cur.execute('''
                        CREATE TABLE Transcripts(
                                transcript_refseq_id TEXT NOT NULL PRIMARY KEY UNIQUE,
                                transcript_ensembl_id TEXT NOT NULL PRIMARY KEY UNIQUE,
                                tx_start INTEGER,
                                tx_end INTEGER,
                                cds_start INTEGER,
                                cds_end INTEGER,
                                gene_refseq_id TEXT,                        
                                exon_count INTEGER,
                                gene_ensembl_id TEXT,
                                protein_refseq_id INTEGER,
                                protein_ensembl_id INTEGER,
                                FOREIGN KEY(gene_refseq_id, gene_ensembl_id) REFERENCES Genes(gene_refseq_id, gene_ensembl_id),
                                FOREIGN KEY(protein_refseq_id,protein_ensembl_id) REFERENCES Proteins(protein_refseq_id,protein_ensembl_id)
                                );'''
                        )
            cur.executescript("DROP TABLE IF EXISTS Exons;")
            print('Creating the table: Exons')
            cur.execute('''
                        CREATE TABLE Exons(
                                gene_refseq_id TEXT,
                                gene_ensembl_id TEXT,        
                                genomic_start_tx INTEGER,
                                genomic_end_tx INTEGER,
                                PRIMARY KEY (gene_refseq_id, gene_ensembl_id, genomic_start_tx, genomic_end_tx),
                                FOREIGN KEY(gene_refseq_id, gene_ensembl_id) REFERENCES Genes(gene_refseq_id, gene_ensembl_id)
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
                                uniprot_id TEXT,
                                gene_refseq_id TEXT,
                                gene_ensembl_id TEXT,
                                transcript_refseq_id TEXT,
                                transcript_ensembl_id TEXT,
                                PRIMARY KEY(protein_refseq_id, protein_ensembl_id),
                                FOREIGN KEY(gene_refseq_id, gene_ensembl_id) REFERENCES Genes(gene_refseq_id, gene_ensembl_id),
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
            if self.merged:
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
        with connect(self.dbName+'.sqlite') as con:
            cur = con.cursor()
            cur.execute('''CREATE INDEX geneTableIndexBySpecies ON Genes(specie);''')
            cur.execute('''CREATE INDEX transcriptTableIndexByGene ON Transcripts(gene_refseq_id) ;''')
            cur.execute(
                '''CREATE INDEX exonsInTranscriptsTableIndexByTranscripts ON Transcript_Exon(transcript_refseq_id) ;''')
            cur.execute('''CREATE INDEX domainEventsTableIndexByProtein ON DomainEvent(protein_refseq_id) ;''')

    def addSpeciesToMerged(self):
        # define self.AllDomains
        return

    def fill_in_db(self, specie):
        """
        This function in for unique species. for more than ine use add Species To Merged
        """

        # if name is not 'merged':
        #    con2 = connect('DB_merged.sqlite')
        #    cur2 = con2.cursor()

        data = Collector(specie)


        with connect(self.dbName + '.sqlite') as con:
            print("Connected to " + self.dbName + "...")
            print("Filling in the tables...")
            cur = con.cursor()
            geneSet = set()
            uExon = set()
            domeve = set()
            dTypeDict = {}
            dNames = {}
            dExt = {}
            dCDD = {}

            # if name is 'merged':
            #   cur2 = cur

            dTypeID = list(cur.execute("SELECT COUNT(*) FROM DomainType"))[0][0]
            cur.execute('SELECT * FROM DomainType')
            for ud in cur.fetchall():
                c_ud = tuple(ud)
                dTypeDict[c_ud[0]] = c_ud[1:]
                dNames[c_ud[1]] = c_ud[0]
                for u_ext in c_ud[5:]:
                    if u_ext is not None:
                        dExt[u_ext] = c_ud[0]
                dCDD[c_ud[4]] = c_ud[0]
            # if name is not 'merged':
            #    con2.close()

            relevantDomains = set()
            for t, d in refGene.items():
                # print(t)
                # break
                tnov = t.split('.')[0]
                if tnov not in g_info.keys():
                    # print('continue')
                    continue
                GeneID = [i.split(':')[-1] for i in g_info[tnov][2] if i.startswith('GeneID')]
                pr = gene2pro[tnov]
                ensID = trans_con.get(t, None)
                # insert into Transcripts table
                values = tuple([t] + d[2:6] + GeneID + [d[6], ensID, p_info[pr][0]])
                cur.execute('''INSERT INTO Transcripts
                            (transcript_id, tx_start, tx_end, cds_start, cds_end, gene_id,
                             exon_count, ensembl_id, protein_id) 
                            VALUES(?,?,?,?,?,?,?,?,?)''', values)

                # insert into Genes table (unique GeneID as primary key)
                if GeneID[0] not in geneSet:
                    MGI = [i.split(':')[-1] for i in g_info[tnov][2] if i.startswith('MGI')]
                    if len(MGI) == 0:
                        MGI = [None]
                    values = tuple(GeneID) + g_info[tnov][0:2] + \
                             tuple(d[0:2] + MGI + [gene_con.get(GeneID[0], None)]) + tuple([specie], )
                    cur.execute(''' INSERT INTO Genes
                                (gene_id, gene_symbol, synonyms, chromosome, strand, MGI_id, ensembl_id, specie)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', values)
                    geneSet.add(GeneID[0])

                # insert into Proteins table
                ensID = protein_con.get(p_info[pr][0], None)
                values = p_info[pr][0:4] + tuple(
                    [ensID, ucsc_acc.get(ensID, [None, None, None, None])[3]] + GeneID + [t])
                # print(values)
                cur.execute(''' INSERT INTO Proteins
                                (protein_id, description, length, synonyms, ensembl_id, uniprot_id, gene_id, transcript_id)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', values)

                # insert into Transcript_Exon table
                start_abs, stop_abs = Tool_code.ucscParser.exons2abs(d[7].copy(), d[8].copy(), d[4:6].copy(), d[1])
                ex_num = 0
                if d[1] == '-':
                    starts = d[7].copy()[::-1]
                    ends = d[8].copy()[::-1]
                else:
                    starts = d[7].copy()
                    ends = d[8].copy()
                # print(len(starts), len(ends), len(start_abs), len(stop_abs))
                for iEx in range(d[6]):
                    # print(iEx)
                    ex_num += 1
                    values = (t, ex_num, starts[iEx], ends[iEx], start_abs[iEx], stop_abs[iEx],)
                    cur.execute(''' INSERT INTO Transcript_Exon
                                (transcript_id, order_in_transcript, genomic_start_tx,\
                                genomic_end_tx, abs_start_CDS, abs_end_CDS)
                                VALUES (?, ?, ?, ?, ?, ?)''', values)

                    # insert into Exons table
                    values = tuple(GeneID) + (starts[iEx], ends[iEx],)
                    if values not in uExon:
                        uExon.add(values)
                        cur.execute('''INSERT INTO Exons
                                    (gene_id, genomic_start_tx, genomic_end_tx)
                                    VALUES (?, ?, ?)''', values)

                if pr in region_dict.keys():
                    splicin = set()
                    for reg in region_dict[pr]:
                        currReg, currExt, dTypeDict, dTypeID, dExt, dNames, dCDD = order_domains.order_domains(reg,
                                                                                                               dTypeDict,
                                                                                                               dTypeID,
                                                                                                               dExt,
                                                                                                               dNames,
                                                                                                               dCDD)
                        relevantDomains.add(currReg)
                        nucStart, nucEnd = ffParser.domain_pos_calc(reg[0], reg[1])
                        # print(nucStart, nucEnd, t)
                        relation, exon_list, length = domain_exon_relationship([nucStart, nucEnd], start_abs, stop_abs)

                        total_length = nucEnd - nucStart + 1  # adding one because coordinates are full-closed!
                        splice_junction = 0
                        complete = 0
                        if relation == 'splice_junction':
                            splice_junction = 1
                            for i in range(len(exon_list)):
                                values = (t, exon_list[i], nucStart, currReg, total_length,
                                          length[i], i + 1,)
                                if values not in splicin:
                                    cur.execute(''' INSERT INTO SpliceInDomains
                                        (transcript_id, exon_order_in_transcript, domain_nuc_start, type_id,\
                                         total_length, included_len, exon_num_in_domain)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)''', values)
                                    splicin.add(values)
                        elif relation == 'complete_exon':
                            complete = 1
                        # insert into domain event table
                        values = (p_info[pr][0], currReg, reg[0], reg[1], total_length,
                                  nucStart, nucEnd, currExt, splice_junction, complete,)
                        if values not in domeve:
                            cur.execute(''' INSERT INTO DomainEvent
                                        (protein_id, type_id, AA_start, AA_end, total_length,\
                                        nuc_start, nuc_end, ext_id, splice_junction, complete_exon)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
                            domeve.add(values)

            if add:
                print('Recreating the table: DomainType and update domains')
                cur.executescript("DROP TABLE IF EXISTS DomainType;")
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
                                    nf TEXT,
                                    cog TEXT,
                                    kog TEXT,
                                    prk TEXT,
                                    tigr TEXT,
                                    other TEXT
                                    );'''
                            )
                # insert into domain type table
                for dom, inf in dTypeDict.items():
                    values = tuple([dom]) + inf
                    cur.execute(''' INSERT INTO DomainType
                                    (type_id, name, other_name, description, CDD_id, cd,cl,\
                                    pfam,smart,nf,cog,kog,prk,tigr,other)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)
            else:
                # insert into domain type table
                for dom in relevantDomains:
                    values = tuple([dom]) + dTypeDict[dom]
                    # print(values)
                    cur.execute(''' INSERT INTO DomainType
                                    (type_id, name, other_name, description,\
                                     CDD_id, cd,cl,pfam,smart,nf,cog,kog,prk,tigr,other)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)



