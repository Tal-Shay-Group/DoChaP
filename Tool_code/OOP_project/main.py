from Tool_code.OOP_project.Director import *
from Tool_code.OOP_project.UcscBuilder import *
from Tool_code.OOP_project.ffBuilder import *
from Tool_code.OOP_project.DB_builder import *

species = 'M_musculus'
ucscbuilder = UcscBuilder(species)
ffbuilder = ffBuilder(species)

director = Director()

director.setBuilder(ucscbuilder)
refGene, ucsc_acc = director.collectFromSource()

director.setBuilder(ffbuilder)
#ff = director.collectFromSource()

#download_refseq_ensemble_connection()
region_dict, p_info, g_info, pro2gene, gene2pro, all_domains, kicked = director.collectFromSource()
gene_con, trans_con, protein_con = gene2ensembl_parser(species)

create_tables_db(species)


def fill_in_db(specie, name, add=True):
    """
    ** the function is using global variables:
        - from flatfile parser: region_dict, p_info, g_info, pro2gene, gene2pro, all_domains
        - from the refGene parser: refGene
    """
    db_name = 'DB_' + name

    #if name is not 'merged':
    #    con2 = connect('DB_merged.sqlite')
    #    cur2 = con2.cursor()

    with connect(db_name + '.sqlite') as con:
        print("Connected to " + db_name + "...")
        print("Filling in the tables...")
        cur = con.cursor()
        geneSet = set()
        uExon = set()
        domeve = set()
        dTypeDict = {}
        dNames = {}
        dExt = {}
        dCDD = {}

        #if name is 'merged':
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
        #if name is not 'merged':
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
            values = tuple(
                [t] + d[2:6] + GeneID + [d[6], ensID, p_info[pr][0]])
            cur.execute('''INSERT INTO Transcripts
                        (transcript_id, tx_start, tx_end, cds_start, cds_end, gene_id,
                         exon_count, ensembl_id, protein_id) 
                        VALUES(?,?,?,?,?,?,?,?,?)''', values)

            # insert into Genes table (unique GeneID as primary key)
            if GeneID[0] not in geneSet:
                MGI = [i.split(':')[-1] for i in g_info[tnov][2] if i.startswith('MGI')]
                if len(MGI) == 0:
                    MGI = [None]
                values = tuple(GeneID) + g_info[tnov][0:2] + tuple(
                    d[0:2] + MGI + [gene_con.get(GeneID[0], None)]) + tuple([specie], )
                cur.execute(''' INSERT INTO Genes
                            (gene_id, gene_symbol, synonyms, chromosome, strand, MGI_id, ensembl_id, specie)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', values)
                geneSet.add(GeneID[0])

            # insert into Proteins table
            ensID = protein_con.get(p_info[pr][0], None)
            values = p_info[pr][0:4] + tuple([ensID, ucsc_acc.get(ensID, [None, None, None, None])[3]] + GeneID + [t])
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
                                                                                                           dExt, dNames,
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


def create_index(db_name):
    with connect('DB_' + db_name + '.sqlite') as con:
        cur = con.cursor()
        cur.execute('''CREATE INDEX geneTableIndexBySpecies ON Genes(specie);''')
        cur.execute('''CREATE INDEX transcriptTableIndexByGene ON Transcripts(gene_id) ;''')
        cur.execute('''CREATE INDEX exonsInTranscriptsTableIndexByTranscripts ON Transcript_Exon(transcript_id) ;''')
        cur.execute('''CREATE INDEX domainEventsTableIndexByProtein ON DomainEvent(protein_id) ;''')


fill_in_db(species, species, add=False)








