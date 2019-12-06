# -*- coding: utf-8 -*-
"""
Created on Sun Oct 20 10:54:41 2019

@author: galozs
"""

import pandas as pd
import sqlite3 as lite
#import gffutils



def import_table (specie, table_name):
    db_name = 'DB_' + specie
    print ("Connecting database: {}...".format(db_name) + " importing table: " + table_name)
    with lite.connect(db_name + '.sqlite') as con:
        return pd.read_sql_query("SELECT * from " + table_name, con)
        
def parse_gtf(gtf_path):
    raw_gtf = pd.read_table(r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\example_gft\merged.gtf', 
                              delimiter='\t', header=None, names=['chr', 'source', 'feature', 
                                                                  'start', 'end', 'score', 
                                                                  'strand', 'frame', 'attribute'])
    
    data = []
    unused = set()
    for row in range(len(raw_gtf)):
        attr = raw_gtf.iloc[row].attribute
        attr = attr.split('; ')
        attr_dict = {}
        for ent in attr:
            #print(ent)
            if ent.startswith('gene_id'):
                attr_dict['gene_id'] = ent[9:-1]
            elif ent.startswith('transcript_id'):
                attr_dict['transcript_id'] = ent[15:-1]
            elif ent.startswith('transcript_name'):
                attr_dict['transcript_name'] = ent[16:-1]
            elif ent.startswith('gene_name'):
                attr_dict['gene_name'] = ent[11:-1]
            elif ent.startswith('nearest_ref'):
                attr_dict['nearest_ref'] = ent[13:-1]
            elif ent.startswith('exon_number'):
                attr_dict['exon_number'] = ent[-2]
            elif ent.startswith('oId'):
                attr_dict['oId'] = ent[5:-1]
            else:
                unused.add(ent.split(' ')[0])
            attr_dict['gene_id'] = attr_dict.get('gene_id', '')
            attr_dict['transcript_id'] = attr_dict.get('transcript_id', '')
            attr_dict['transcript_name'] = attr_dict.get('transcript_name', '')
            attr_dict['gene_name'] = attr_dict.get('gene_name', '')
            attr_dict['nearest_ref'] = attr_dict.get('nearest_ref', '')
            attr_dict['exon_number'] = attr_dict.get('exon_number', '')
            attr_dict['oId'] = attr_dict.get('oId', '')
        data.append(attr_dict)
    attr_df = pd.DataFrame(data)
        
    #db=gffutils.create_db(r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\example_gft\merged.gtf',
    #                      dbfn = 'example_gtf.db')
    #db = gffutils.FeatureDB('example_gtf.db')
    merged = raw_gtf.merge(attr_df, left_index=True, right_index=True)    
     
if __name__ == "__main__":
    specie = 'M_musculus'
    Transcripts, Exons, Transcript_Exon, Genes, Proteins, DomainType, DomainEvent, SpliceInDomains = map(import_table, [specie] * 8,
                                                                                                         ['Transcripts', 'Exons', 
                                                                                                          'Transcript_Exon', 'Genes',
                                                                                                          'Proteins', 'DomainType', 
                                                                                                          'DomainEvent', 'SpliceInDomains'])

    	
    
