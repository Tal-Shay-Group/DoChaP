# -*- coding: utf-8 -*-
"""
Parse gbff gpff files
Created on Wed Jun 19 12:08:28 2019

@author: galozs
"""

from Bio import SeqIO

#gbff = [f[1] for f in gbff]
#gpff = [f[1] for f in gpff]
#gpff_path =r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\Tool_code\data\M_musculus\flatfiles\mouse.1.protein.gpff'
#gpff2 =r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\Code\data\M_musculus\flatfiles\mouse.2.protein.gpff'
#gpff = r"C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\Tool_code\data\H_sapiens\flatfiles\human.2.protein.gpff"
#gbff =r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\Code\data\M_musculus\flatfiles\mouse.1.rna.gbff'

def parse_all_gpff(file_list):
    regions = {}
    p_info = {}
    g_info = {}
    pro2gene = {}
    gene2pro = {}
    all_domains = set()
    kicked = []
    for file in file_list:
        reg, p, g, p2g, g2p, dom, kic = parse_gpff(file)
        regions.update(reg)
        p_info.update(p)
        g_info.update(g)
        pro2gene.update(p2g)
        gene2pro.update(g2p)
        all_domains = all_domains.union(dom)
        kicked =  kicked + kic
    return regions, p_info, g_info, pro2gene, gene2pro, all_domains, kicked

 
def parse_gpff(gpff_path):
    '''Parse protein data from all gbff files using Bio.SeqIO'''
    #records = []
    region_dict = {}
    p_info = {}
    g_info = {}
    all_domains = set()
    pro2gene = {}
    gene2pro = {}
    kicked = [] 
    for rec in SeqIO.parse(gpff_path, 'gb'):
        #records.append(rec)
        ##rec.name is without version ; rec.id is with version
        #print(rec.id)
        if rec.name in p_info.keys():
            raise('redundancy err ' + rec.name)
        if rec.name[0:2] == 'NP' or rec.name[0:2] == 'XP': # takes both proteins and predictions! 
            info, gene, gene_info = protein_info(rec)
            p_info[rec.name] = info[1:]
            genekey = gene.split('.')[0]
            g_info[genekey] = gene_info
            pro2gene[rec.name] = gene
            gene2pro[genekey] = rec.name 
            rr, dd, kic = regions_from_record(rec) 
            region_dict[rec.name] = rr
            all_domains = all_domains.union(dd)
            kicked = kicked + kic
    return region_dict, p_info, g_info, pro2gene, gene2pro, all_domains, kicked


def regions_from_record(record):
    '''
    This functions takes a record from a gpff file and parse it by finding all the features defined Regions
    and put them in a list of tuples where each tuple include the following information about the region:
        1- start position in the protein + 1 as all records are 0-based start!!!)
        2- end position in the protein (all records are 1-based stop!!!)
        3- name of the region
        4- note of the region - description
        5- id of the region based on the source (can start with pfam/smart/cl/cd etc...)
    The function returns a list of the regions in the record and a set of all the domains identified in this record.
    '''
    regions = [feature for feature in record.features if feature.type == 'Region']
    parsed = []
    domains = set()
    kicked = []
    for reg in regions:
        start = reg.location.start.position + 1# all records are 0 based start!!!
        end = reg.location.end.position
        if len(reg.qualifiers) > 1 and 'region_name' in reg.qualifiers and start != end: #only looking at regions larger than 1
            name = reg.qualifiers['region_name'][0]                                
            if 'note' in reg.qualifiers:
                note = reg.qualifiers['note'][0]
            else:
                note = None
            #cdId = note.split('; ')[-1]
            #print(name)
            if name.startswith('PRK'):
                ext_id = name
            elif note != None:
                if 'propagated from UniProtKB' in note:
                    note = note
                    ext_id = None
                elif ';' in note:
                    noteSplit = note.split('; ')
                    ext_id = noteSplit[-1]
                    note = note[:-len(ext_id)]
                else:
                    ext_id = None
            else:
                ext_id = None
            if 'db_xref' not in reg.qualifiers:
                if ext_id == None:
                    kicked.append(note)
                    continue
                cdId = None
                domains = domains.union(set([ext_id]))
            else:
                cdId = reg.qualifiers['db_xref'][0].split(':')[1]
                domains = domains.union(set([cdId]))
            parsed.append((start, end, name, note, ext_id, cdId))
    return parsed, domains, kicked

def protein_info(record):
    '''
    This function takes s protein record of a gpff file and parse it to get all the protein information.
    it returns a tuple including the following information:
        1- refseq_id (not including the version)
        2- version of the sequence (full id will be refseq_id.version)
        3- product protein description
        4- length (number of aa)
    it also returns a string with the refseq_id of the gene
    '''
    withversion = record.id # with version
    refseq_id = record.name #without version
    descr = record.description
    pro = [p for p in record.features if p.type == 'Protein'][0]
    length = pro.location.end.position # length!!!
    try:
        note = pro.qualifiers['note'][0]
    except Exception:
        note = None
    cds = [c for c in record.features if c.type == 'CDS'][0]
    gene = cds.qualifiers['coded_by'][0].split(':')[0]
    gene_info = (cds.qualifiers.get('gene', [None])[0], cds.qualifiers.get('gene_synonym',[None])[0], cds.qualifiers.get('db_xref',[]))
    return (refseq_id, withversion, descr, length, note,), gene , gene_info    


    
#region_dict1, p_info1, g_info1, pro2gene1, gene2pro1, all_domains1, kicked = parse_gpff(gpff)
#region_dict2, p_info2, g_info2, pro2gene2, gene2pro2, all_domains2 = parse_gpff(gpff2)

def domain_pos_calc(AAstart, AAend):
    nucStart = (AAstart * 3) - 2 #start position, including
    nucEnd = AAend * 3 # end position, including!!!
    return nucStart, nucEnd
    


    
    
    
    