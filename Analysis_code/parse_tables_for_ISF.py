# -*- coding: utf-8 -*-
"""
Created on Sun Oct 27 16:03:15 2019

@author: galozs
"""

# TODO:
# in human and mouse -
# for each gene - 
# number of transcripts, number of unique exons, number of exons in the transcript with most exons

import pandas as pd
import sqlite3 as lite



def import_table (specie, table_name):
    db_name = r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\Tool_code\DB_' + specie
    print ("Connecting database: {}...".format(db_name))
    with lite.connect(db_name + '.sqlite') as con:
        return pd.read_sql_query("SELECT * from " + table_name, con)

    
def maketables(specie):
    Transcripts, Exons, Transcript_Exon, Genes = map(import_table, [specie] * 4, ['Transcripts', 'Exons', 
                                                 'Transcript_Exon', 'Genes'])
    countT = Transcripts.groupby('gene_id').count()['transcript_id'] # how many transcripts per gene
    Uexon = Exons['gene_id'].value_counts() # how many times each gene exists
    Uexon.index.name = 'gene_id'
    Uexon.index = Uexon.index.map(int)
    df = pd.concat([countT, Uexon], axis=1)
    df.columns = ['TranscriptsNumber', 'UniqueExonsPerGene']
    maxEx = pd.DataFrame(Transcripts.groupby('gene_id').exon_count.max()) # number of exons to the transcript with most exons
    df2 = df.merge(maxEx, on = 'gene_id')
    df2.columns = ['TranscriptsNumber', 'UniqueExonsPerGene', 'MaxExonPerTranscript']
    genedf = pd.DataFrame({'GeneSymbol':Genes.set_index('gene_id')['gene_symbol']})
    genedf.index.name = 'gene_id'
    genedf.index = genedf.index.map(int)
    df3 = df2.merge(genedf, on = 'gene_id')
    
    df3 = df3[['GeneSymbol', 'TranscriptsNumber', 'UniqueExonsPerGene', 'MaxExonPerTranscript']]
    df3.index.name = 'EntrezGeneID'
    df3.to_csv('{}.gene_transcript_exon.csv'.format(specie))
    print("writing table '{}.gene_transcript_exon.csv'")
    
if __name__ == "__main__":
    specie = 'H_sapiens' #'M_musculus'
    maketables(specie)
    
