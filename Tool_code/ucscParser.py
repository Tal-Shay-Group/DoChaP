# -*- coding: utf-8 -*-
"""
Created on Sun Jun  2 15:43:57 2019

@author: galozs
"""
import os


def parse_kgXref(specie, kgXref_path = os.getcwd() + '/data/{}/from_ucsc/kgXref.txt'):
     # kgID;mRNA;spID;spDisplayID;geneSymbol;refseq;protAcc;description;rfamAcc;tRnaName
    kgXref = {}
    with open(kgXref_path.format(specie), 'r') as Xref:
        for line in Xref:
            ll = line.strip().split('\t')
            kgXref[ll[0]] = ll[1:]
    return kgXref


def parse_ncbiRefSeq(specie, table_path = os.getcwd() + '/data/{}/from_ucsc/ncbiRefSeq.txt'):
    '''
    Parse the refGene table with the columns:
        bin;name;chrom;strand;txStart;txEnd;cdsStart;cdsEnd;exonCount;exonStarts;exonEnds;score;name2;cdsStartStat;cdsEndStat;exonFrames
    To a dictionary with refseqID as keys and he following list as the value:
        chromosome, strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, geneSymbol
    '''
    ncbiRefSeq = {}
    with open(table_path.format(specie), 'r') as refS:
        for line in refS:
            ll = line.strip().split('\t')
            ex_starts = [int(start) for start in ll[9].split(',') if len(start) > 0]
            ex_ends = [int(ends) for ends in ll[10].split(',') if len(ends) > 0]
            ncbiRefSeq[ll[1]] = ncbiRefSeq.get(ll[1], 
                               [ll[2], ll[3]] + list(map(int,ll[4:9]))+ [ex_starts, ex_ends, ll[12]])
    return ncbiRefSeq


def parse_knownGene(specie, kgXref, knownGene_path = os.getcwd() + '/data/{}/from_ucsc/knownGene.txt'):
    '''
    Parse the knownGene table with the columns:
        name;chrom;strand;txStart;txEnd;cdsStart;cdsEnd;exonCount;exonStarts;exonEnds;proteinID;alignID
    To a dictionary with refseqID as keys and he following list as the value:
        chromosome, strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, geneSymbol 
    ''' 
    knownGene = {}
    with open(knownGene_path.format(specie), 'r') as known:
        for line in known:
            ll = line.strip().split('\t')
            ex_starts = [int(start) for start in ll[8].split(',') if len(start) > 0]
            ex_ends = [int(ends) for ends in ll[9].split(',') if len(ends) > 0]
            geneSymb = kgXref.get(ll[0], '   ')[3]
            ucsc = ll[11]
            knownGene[ll[0]] = knownGene.get(ll[0], 
                               ll[1:3] + list(map(int,ll[3:8])) + [ex_starts, ex_ends, geneSymb, ucsc])
    return knownGene

#kgXref = parse_kgXref('M_musculus')
#ncbiRefSeq = parse_ncbiRefSeq('M_musculus', r'C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP_Shani\Tool_code\data\{}\from_ucsc\refGene.txt')
#knownGene = parse_knownGene('M_musculus', kgXref)

def MatchAcc_ucsc(refseq, ensembl, kgXref):
    all_aliases = {} # contain tuples of (refseq, UCSC, GENESYMB, UNIPROT)
    for uid,entry in kgXref.items():
        ucsc = ensembl[uid][10]
        tup = (entry[4], ucsc, entry[3], entry[1],)
        all_aliases[uid] = tup
    return all_aliases

#ucsc_acc = MatchAcc_ucsc(ncbiRefSeq, knownGene, kgXref)
  
def gene2ensembl_parser(specie, ucsc_acc, filelocation = os.getcwd() + '/data/'):
    '''
    This function uses the table gene2ensembl from refseq database to create all connections 
    between RefSeq and ENSEMBL for gene, transcript, protein
    Table columns: table columns: 
    taxID;geneID;ENS_GeneID;refseq_transcript;ENS_transcript;refseq_protein;ENS_protein
    '''
    taxID = {'M_musculus': 10090, 'H_sapiens': 9606}
    #print(taxID[specie])
    tablename = 'gene2ensembl.txt' 
    gene_con = {}
    trans_con = {}
    protein_con = {}
    with open(filelocation + tablename, 'r') as g2e:
        for line in g2e:
            ll = line.strip().split('\t')
            #print(ll)
            if ll[0] == str(taxID[specie]):
                #print(ll[0])
                gene_con[ll[1]] = gene_con.get(ll[1], ll[2]) 
                trans_con[ll[3]] = [ll[4], ucsc_acc.get(ll[4], '    ')[1]]
                protein_con[ll[5]] = [ll[6], ucsc_acc.get(ll[4], '    ')[3]]
    return gene_con, trans_con, protein_con
    
def exons2abs(start_list, stop_list, CDS, strand):
    '''
    This function takes two lists (or tuples) one for all the starts 
    and one for all the ends of the exons of a specific transcript
    and transform them into absilute positions in the transcript. 
    for genes on '-' strand - reverse the start and end list.
    '''
    if len(start_list) != len(stop_list):
        raise ValueError('Arguments 1 and 2: Expected same length for the lists/tuples of start and stop positions')
    elif len(CDS) != 2:
        raise ValueError('3rd argument: Expected list of 2 values: CDS_start, CDS_end')
    elif strand != '-' and strand != '+':
        raise ValueError('4th argument: Expected strand to string of + or -, for forward and reverse (respectievly)')
    transcript_len = 0
    abs_start = []
    abs_stop = []    
    add_opt = 0
    if strand == '-':
        stop_list = stop_list[::-1]
        start_list = start_list[::-1]
        add_opt = 1
    for i in range(len(start_list)):
        #print('start' + str(start_list[i]))
        #print('end ' + str(stop_list[i]))
        if stop_list[i] < CDS[0]:
            #print('cond1, iter:' + str(i))
            abs_start.append(0)
            abs_stop.append(0)
            continue
        elif start_list[i] < CDS[0] and stop_list[i] > CDS[0]:
            start_list[i] = CDS[0]
            #print('cond2, iter:' + str(i))
        if start_list[i] > CDS[1]:
            #print('cond3, iter:' + str(i))
            abs_start.append(0)
            abs_stop.append(0)
            continue
        elif stop_list[i] > CDS[1] and start_list[i] < CDS[1]:
            stop_list[i] = CDS[1] + add_opt
            #print('cond4, iter:' + str(i))
        abs_start.append(transcript_len + 1)
        curr_length = stop_list[i] - start_list[i]
        abs_stop.append(transcript_len + curr_length)
        transcript_len = transcript_len + curr_length    
    return abs_start, abs_stop

##NM_001283048
#start_list = [91147571, 91151709, 91152628, 91153085, 91153278, 91158748, 91164043, 91165943, 91170286]
#stop_list = [91149758, 91151797,91152738, 91153180, 91153397, 91158845, 91164201, 91166069, 91170550]
#exons2abs(start_list, stop_list, [91149475, 91151746], '-')

#NM_001162506
#exmp2_start = [99074972, 99075349, 99075607, 99077287, 99077528, 99077831, 99078246, 99078783, 99080865, 99081190, 99081834, 99082125, 99082908, 99083227]
#exmp2_stop = [99075067, 99075498, 99075797, 99077445, 99077666, 99077911, 99078323, 99078902, 99080949, 99081250, 99081969, 99082705, 99083102, 99083409]
#exons2abs(exmp2_start, exmp2_stop, [99075354, 99083275], '+')


def compare_source_exons(refGene, knownGene, kgXref):
    match = set()
    mismatch = set()
    CDSnoExons = set()
    unConnected = set()
    ENSnoRef = set()
    RefnoEns = set(refGene.keys())
    nms = set(refGene.keys())
    ens = set(knownGene.keys())
    for trans in ens:
        conect = kgXref.get(trans, -1)
        ref = conect[0]
        if conect == -1 or ref == '':
            unConnected.add(trans)
        elif refGene.get(ref, -1) == -1:
            ENSnoRef.add(trans)
        elif knownGene[trans][4] == refGene[ref][4] and knownGene[trans][5] == refGene[ref][5]:
            nms -= set(ref)
            if ([knownGene[trans][4]]+knownGene[trans][7][1:] == [refGene[ref][4]] +refGene[ref][7][1:] 
            and knownGene[trans][8][:-1]+[knownGene[trans][5]] == refGene[ref][8][:-1]+[refGene[ref][5]]):
                match.add(trans)
            else:
                CDSnoExons.add(trans)
        else:
            mismatch.add(trans)
            nms -= set(ref)
    

            
    
