# -*- coding: utf-8 -*-
"""
Created on Mon Nov 25 16:27:43 2019
This Module is used to build MERGED databases only
@author: galozs
"""

import sqlite3 as lite
import ucscParser
import ffParser
#import csv
import ffDownloader


def create_tables_db():
    """
    Create a transcripts table in the specie database and fills with ucsc transcripts data


    """
    db_name = 'DB_merged'
    print ("Creating database: {}...".format(db_name))
    with lite.connect(db_name + '.sqlite') as con:
        cur = con.cursor()
        cur.executescript("DROP TABLE IF EXISTS transcripts;")
        print('Creating the table: Transcripts')
        cur.execute('''
                    CREATE TABLE Transcripts(
                            transcript_id TEXT NOT NULL PRIMARY KEY UNIQUE,
                            tx_start INTEGER,
                            tx_end INTEGER,
                            cds_start INTEGER,
                            cds_end INTEGER,
                            gene_id TEXT,                        
                            exon_count INTEGER,
                            ensembl_ID TEXT,
                            ucsc_id TEXT,
                            protein_id INTEGER,
                            FOREIGN KEY(gene_id) REFERENCES Genes(gene_id),
                            FOREIGN KEY(protein_id) REFERENCES Proteins(protein_id)
                            );'''
                            )
        cur.executescript("DROP TABLE IF EXISTS Exons;")
        print('Creating the table: Exons')
        cur.execute('''
                    CREATE TABLE Exons(
                            gene_id TEXT,        
                            genomic_start_tx INTEGER,
                            genomic_end_tx INTEGER,
                            PRIMARY KEY (gene_id, genomic_start_tx, genomic_end_tx),
                            FOREIGN KEY(gene_id) REFERENCES Genes(gene_id)
                            );'''
                            )
        
        cur.executescript("DROP TABLE IF EXISTS Transcript_Exon;")
        print('Creating the table: Transcript_Exon')
        cur.execute('''
                    CREATE TABLE Transcript_Exon(
                            transcript_id TEXT,
                            order_in_transcript INTEGER,
                            genomic_start_tx INTEGER,
                            genomic_end_tx INTEGER,
                            abs_start_CDS INTEGER,
                            abs_end_CDS INTEGER,
                            PRIMARY KEY(transcript_id, order_in_transcript),
                            FOREIGN KEY(transcript_id) REFERENCES Transcripts(transcript_id),
                            FOREIGN KEY(genomic_start_tx, genomic_end_tx) REFERENCES Exons(genomic_start_tx, genomic_end_tx)
                            );'''
                            )
        
        cur.executescript("DROP TABLE IF EXISTS Genes;")
        print('Creating the table: Genes')
        cur.execute('''
                    CREATE TABLE Genes(
                            gene_id TEXT NOT NULL PRIMARY KEY UNIQUE,
                            gene_symbol TEXT,
                            synonyms TEXT,
                            chromosome TEXT,
                            strand TEXT,
                            MGI_id TEXT,
                            ensembl_id TEXT,
                            description TEXT,
                            specie TEXT
                            );'''
                            )
        cur.executescript("DROP TABLE IF EXISTS Proteins;")
        print('Creating the table: Proteins')
        cur.execute('''
                    CREATE TABLE Proteins(
                            protein_id TEXT NOT NULL PRIMARY KEY UNIQUE,
                            description TEXT,
                            synonyms TEXT,
                            length INTEGER,
                            ensembl_id TEXT,
                            uniprot_id TEXT,
                            gene_id TEXT,
                            transcript_id TEXT,
                            FOREIGN KEY(gene_id) REFERENCES Genes(gene_id),
                            FOREIGN KEY(transcript_id) REFERENCES Transcripts(transcript_id)
                            );'''
                            )
        cur.executescript("DROP TABLE IF EXISTS DomainType;")
        print('Creating the table: DomainType')
        cur.execute('''
                    CREATE TABLE DomainType(
                            type_id INTEGER AUTO INCREMENT NOT NULL PRIMARY KEY UNIQUE,
                            name TEXT,
                            description TEXT,
                            external_id TEXT,
                            CDD_id INTEGER
                            );'''
                            )
        cur.executescript("DROP TABLE IF EXISTS DomainEvent;")
        print('Creating the table: DomainEvent')
        cur.execute('''
                    CREATE TABLE DomainEvent(
                            protein_id TEXT,
                            type_id INTEGER,
                            AA_start INTEGER,
                            AA_end INTEGER,
                            nuc_start INTEGER,
                            nuc_end INTEGER,
                            total_length INTEGER,
                            splice_junction BOOLEAN,
                            complete_exon BOOLEAN,
                            PRIMARY KEY(protein_id, type_id, AA_start, total_length),
                            FOREIGN KEY(type_id) REFERENCES DomainType(type_id),
                            FOREIGN KEY(protein_id) REFERENCES Proteins(protein_id)
                            );'''
                            )
        cur.executescript("DROP TABLE IF EXISTS SpliceInDomains;")
        print('Creating the table: SpliceInDomains')
        cur.execute('''
                    CREATE TABLE SpliceInDomains(
                            transcript_id TEXT,
                            exon_order_in_transcript INTEGER,
                            type_id INTEGER,
                            total_length INTEGER,
                            domain_nuc_start INTEGER,
                            included_len INTEGER,
                            exon_num_in_domain INTEGER,
                            PRIMARY KEY (transcript_id, exon_order_in_transcript, type_id, total_length, domain_nuc_start),
                            FOREIGN KEY(transcript_id) REFERENCES Transcripts(transcript_id),
                            FOREIGN KEY(exon_order_in_transcript) REFERENCES Transcript_Exon(order_in_transcript),
                            FOREIGN KEY(type_id) REFERENCES DomainType(id)
                            FOREIGN KEY(domain_nuc_start, total_length) REFERENCES DomainEvent(Nuc_start, total_length)
                            );'''
                            )
    
def domain_exon_relationship(domain_nuc_positions, exon_starts, exon_ends):
    for ii in range(len(exon_starts)):
        if domain_nuc_positions[0] >= exon_starts[ii] and domain_nuc_positions[0] <= exon_ends[ii]:
            if domain_nuc_positions[1] <= exon_ends[ii]:
                return 'complete_exon' , ii+1, domain_nuc_positions[1] - domain_nuc_positions[0] + 1
            else:
                flag = 0
                jj = ii+1
                length = [-1*(exon_ends[ii] - domain_nuc_positions[0] + 1)]
                while flag == 0 and jj < len(exon_starts):
                    if domain_nuc_positions[1] >= exon_starts[jj] and domain_nuc_positions[1] <= exon_ends[jj]:
                        flag = 1
                        length.append(domain_nuc_positions[1] - exon_starts[jj] + 1)
                    else:
                        length.append(exon_ends[jj] - exon_starts[jj] + 1)
                    jj += 1
                return 'splice_junction', list(range(ii+1, jj+1)), length

    return None, None, None
        
        
def fill_in_db(specie, add=True):
    '''
    ...
    ** the function is using global variables:
        - from flatfile parser: region_dict, p_info, g_info, pro2gene, gene2pro, all_domains
        - from the refGene parser: refGene
    '''
    #parse_files for specie
    refGene = ucscParser.parse_ncbiRefSeq(specie)
    kgXref = ucscParser.parse_kgXref(specie)
    knownGene = ucscParser.parse_knownGene(specie, kgXref)
    ucsc_acc = ucscParser.MatchAcc_ucsc(refGene, knownGene, kgXref)
    gene_con, trans_con, protein_con = ucscParser.gene2ensembl_parser(specie, ucsc_acc)
    
    db_name = 'DB_merged'
    with lite.connect(db_name + '.sqlite') as con:
        cur = con.cursor()        
        geneSet = set()
        if add:
            dTypeID = list(cur.execute("SELECT COUNT(*) FROM DomainType"))[0][0]
        else: 
            dTypeID = 0
        dTypeDict = {}
        uExon =set()
        for t, d in refGene.items():
            #print(t)
            #break
            if t not in g_info.keys():
                #print('continue')
                continue
            GeneID = [i.split(':')[-1] for i in g_info[t][2] if i.startswith('GeneID')]
            
            '''insert into transcript table'''
            values = tuple([t] + d[2:6] + GeneID + [d[6]]+ trans_con.get(t, ['', '']) + [gene2pro[t]])
            cur.execute('''INSERT INTO Transcripts 
                        (transcript_id, tx_start, tx_end, cds_start, cds_end, gene_id, exon_count, ensembl_id, ucsc_id, protein_id) 
                        VALUES(?,?,?,?,?,?,?,?,?,?)''',values)
            
            '''insert into Genes table (unique GeneID as primary key)'''
            if GeneID[0] not in geneSet:
                MGI = [i.split(':')[-1] for i in g_info[t][2] if i.startswith('MGI')]
                if len(MGI) == 0:
                    MGI = ['']
                values = tuple(GeneID) + g_info[t][0:2] + tuple(d[0:2] + MGI + [gene_con.get(GeneID[0], '')]) + tuple([specie],)
                cur.execute(''' INSERT INTO Genes
                            (gene_id, gene_symbol, synonyms, chromosome, strand, MGI_id, ensembl_id, specie)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', values)
                geneSet.add(GeneID[0])

                    
            '''insert into Proteins table'''
            pr = gene2pro[t]
            values = tuple([pr]) + p_info[pr][1:4] + tuple(protein_con.get(pr, ['', '']) + GeneID + [t])
            #print(values)
            cur.execute(''' INSERT INTO Proteins
                            (protein_id, description, length, synonyms, ensembl_id, uniprot_id, gene_id, transcript_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', values)
            
            ''' insert into Transcript_Exon table'''
            start_abs, stop_abs = ucscParser.exons2abs(d[7].copy(), d[8].copy(), d[4:6].copy(), d[1])
            ex_num = 0
            if d[1] == '-':
                starts = d[7].copy()[::-1]
                ends = d[8].copy()[::-1]
            else:
                starts = d[7].copy()
                ends = d[8].copy()
            #print(len(starts), len(ends), len(start_abs), len(stop_abs))
            for iEx in range(d[6]):
                #print(iEx)
                ex_num += 1
                values = (t, ex_num, starts[iEx], ends[iEx], start_abs[iEx], stop_abs[iEx],)
                cur.execute(''' INSERT INTO Transcript_Exon
                            (transcript_id, order_in_transcript, genomic_start_tx,  genomic_end_tx, abs_start_CDS, abs_end_CDS)
                            VALUES (?, ?, ?, ?, ?, ?)''', values)
                
                '''insert into Exons table'''
                values =tuple(GeneID) + (starts[iEx], ends[iEx],)
                if values not in uExon:
                    uExon.add(values)
                    cur.execute('''INSERT INTO Exons
                                (gene_id, genomic_start_tx, genomic_end_tx)
                                VALUES (?, ?, ?)''', values)
            
            ''' insert into domain event table'''
            if pr in region_dict.keys():
                for reg in region_dict[pr]:
                    if (reg[2], reg[5],) not in dTypeDict.keys():
                        dTypeID += 1
                        dTypeDict[(reg[2], reg[5],)] = dTypeID
                        values = (dTypeID,) + reg[2:]
                        cur.execute(''' INSERT INTO DomainType
                                    (type_id, name, description, external_id, CDD_id)
                                    VALUES (?, ?, ?, ?, ?)''', values) 
                        
                    nucStart, nucEnd = ffParser.domain_pos_calc(reg[0], reg[1])
                    #print(nucStart, nucEnd, t)
                    relation, exon_list, length = domain_exon_relationship([nucStart, nucEnd], start_abs, stop_abs)
                    
                    total_length = nucEnd - nucStart + 1 # adding one because coordinates are full-closed!
                    splice_junction = 0
                    complete = 0
                    if relation == 'splice_junction':
                        splice_junction = 1
                        for i in range(len(exon_list)):
                            values = (t, exon_list[i], nucStart, dTypeDict[(reg[2], reg[5],)], total_length,
                                            length[i], i + 1,)
                            cur.execute(''' INSERT INTO SpliceInDomains
                                    (transcript_id, exon_order_in_transcript, domain_nuc_start, type_id, total_length, included_len, exon_num_in_domain)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)''', values)
                    elif relation == 'complete_exon':
                        complete = 1
                    values = (pr, dTypeDict[(reg[2], reg[5],)], reg[0], reg[1], total_length,
                                            nucStart, nucEnd, splice_junction, complete,)
                    cur.execute(''' INSERT INTO DomainEvent
                                    (protein_id, type_id, AA_start, AA_end, total_length, nuc_start, nuc_end, splice_junction, complete_exon)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', values)

           
            
if __name__ == "__main__":
    specie = 'M_musculus'#'H_sapiens' #  #'M_musculus_small'
    # files for flatfiles parser
    
    # Redownload
    #gbff_list, gpff_list = ffDownloader.download_flatfiles(specie)
    #gpff_path = [f[1] for f in gpff_list]
    #ffDownloader.download_refseq_ensemble_connection()
    #ffDownloader.download_ucsc_tables(specie)
    
    # Don't rerun - path for mouse
    gpff_path =[r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\Tool_code\data\M_musculus\flatfiles\mouse.1.protein.gpff', 
           r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\Tool_code\data\M_musculus\flatfiles\mouse.2.protein.gpff']
    
    # Don't rerun - path for mouse small
    #gpff_path = [r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\Code\data\M_musculus_small\flatfiles\mouse.2.protein.small5.gpff']
    
    # Don't rerun - path for human
    #dirpath='data/H_sapiens/flatfiles/'
    #dirpath = r"C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\Tool_code\data\H_sapiens\flatfiles"
    #gpff_path = [dirpath+'\human.2.protein.gpff', dirpath+'\human.1.protein.gpff', dirpath+'\human.7.protein.gpff',
         #        dirpath+'\human.4.protein.gpff', dirpath+'\human.5.protein.gpff', dirpath+'\human.8.protein.gpff', dirpath+'\human.6.protein.gpff', dirpath+'\human.3.protein.gpff']
    
    #parse
    region_dict, p_info, g_info, pro2gene, gene2pro, all_domains, kicked = ffParser.parse_all_gpff(gpff_path)
    #create_tables_db()
    fill_in_db(specie)




