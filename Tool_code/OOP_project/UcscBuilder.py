import ftplib
import gzip
import os
from recordTypes import *

from Director import SourceBuilder


class UcscBuilder(SourceBuilder):
    """
    Download and parse UCSC tables
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        ucsc_conversion = {'M_musculus': 'mm10', 'H_sapiens': 'hg38', 'R_norvegicus': 'rn6', 'D_rerio': 'danRer11',
                           'X_tropicalis': 'xenTro9'}
        self.ucscSpecies = ucsc_conversion[self.species]

    def downloader(self):
        specie = self.species
        username = 'anonymous'
        pswd = 'example@post.bgu.ac.il'
        skey = self.ucscSpecies

        ftp_address = 'hgdownload.soe.ucsc.edu'
        print('connecting to: ' + ftp_address + '...')
        ftp = ftplib.FTP(ftp_address)
        print('logging in...')
        ftp.login(user=username, passwd=pswd)
        ftp_path = '/goldenPath/{}/database/'
        ftp.cwd(ftp_path.format(skey))
        download_path = os.getcwd() + '/data/{}/from_ucsc/'
        print('downloading files to : ' + download_path.format(self.species))
        os.makedirs(os.path.dirname(download_path.format(self.species)), exist_ok=True)
        tables = ['refGene', 'kgXref', 'knownGene', 'ncbiRefSeq']
        allTables = ftp.nlst()
        for table in tables:
            if table + '.txt.gz' not in allTables:
                print('Table ' + table + ' not exist for species: ' + specie)
                continue
            table_path = download_path.format(self.species) + table + '.txt'
            print('downloading: ' + table + '.txt.gz..')
            ftp.sendcmd("TYPE i")
            with open(table_path + '.gz', 'wb') as f:
                def callback(chunk):
                    f.write(chunk)

                ftp.retrbinary("RETR " + table + '.txt.gz', callback)
            print('extracting...')
            inp = gzip.GzipFile(table_path + '.gz', 'rb')
            s = inp.read()
            inp.close()
            with open(table_path, 'wb') as f_out:
                f_out.write(s)
            print('removing compressed file...')
            os.remove(table_path + '.gz')

    def parse_kgXref(self, kgXref_path=os.getcwd() + '/data/{}/from_ucsc/kgXref.txt'):
        # kgID;mRNA;spID;spDisplayID;geneSymbol;refseq;protAcc;description;rfamAcc;tRnaName
        kgXref = {}
        with open(kgXref_path.format(self.species), 'r') as Xref:
            for line in Xref:
                ll = line.strip().split('\t')
                kgXref[ll[0]] = ll[1:]
        return kgXref

    def parse_ncbiRefSeq(self, table_path=os.getcwd() + '/data/{}/from_ucsc/ncbiRefSeq.txt'):
        """
        Parse the refGene table with the columns:
            bin;name;chrom;strand;txStart;txEnd;cdsStart;cdsEnd;exonCount;exonStarts;exonEnds;score;name2;cdsStartStat;cdsEndStat;exonFrames
        To a dictionary with refseqID as keys and he following list as the value:
            chromosome, strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, geneSymbol
        """
        ncbiRefSeq = dict()
        ncbiRefSeq = list()
        with open(table_path.format(self.species), 'r') as refS:
            for line in refS:
                ll = line.strip().split('\t')
                ex_starts = [int(start) for start in ll[9].split(',') if len(start) > 0]
                ex_ends = [int(ends) for ends in ll[10].split(',') if len(ends) > 0]
                #ncbiRefSeq[ll[1]] = ncbiRefSeq.get(ll[1],
                #                                   [ll[2], ll[3]] + list(map(int, ll[4:9])) + [ex_starts, ex_ends,
                #                                                                               ll[12]])
                newT = Transcript(refseq=ll[1], ensembl=None, chrom=ll[2], strand=ll[3], tx=tuple(map(int,ll[4:6])), CDS=tuple(map(int,ll[6:8])),
                                  gene=ll[12], prot_ref=None, exons_starts=ex_starts, exons_ends=ex_ends)
                ncbiRefSeq.append(newT)
        return ncbiRefSeq

    def parse_knownGene(self, kgXref, knownGene_path=os.getcwd() + '/data/{}/from_ucsc/knownGene.txt'):
        """
        Parse the knownGene table with the columns:
            name;chrom;strand;txStart;txEnd;cdsStart;cdsEnd;exonCount;exonStarts;exonEnds;proteinID;alignID
        To a dictionary with refseqID as keys and he following list as the value:
            chromosome, strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, geneSymbol
        """
        knownGene = {}
        with open(knownGene_path.format(self.species), 'r') as known:
            for line in known:
                ll = line.strip().split('\t')
                ex_starts = [int(start) for start in ll[8].split(',') if len(start) > 0]
                ex_ends = [int(ends) for ends in ll[9].split(',') if len(ends) > 0]
                geneSymb = kgXref.get(ll[0], '   ')[3]
                ucsc = ll[11]
                knownGene[ll[0]] = knownGene.get(ll[0],
                                                 ll[1:3] + list(map(int, ll[3:8])) + [ex_starts, ex_ends, geneSymb,
                                                                                      ucsc])
        return knownGene

    def MatchAcc_ucsc(self, ensembl, kgXref):
        all_aliases = {}  # contain tuples of (refseq, UCSC, GENESYMB, UNIPROT)
        for uid, entry in kgXref.items():
            ucsc = ensembl[uid][10]
            tup = (entry[4], ucsc, entry[3], entry[1],)
            all_aliases[uid] = tup
        return all_aliases

    def parser(self):
        kgXref = self.parse_kgXref()
        aliases = self.MatchAcc_ucsc(self.parse_knownGene(kgXref), kgXref)
        return self.parse_ncbiRefSeq(), aliases

    def records(self):
        """
        Here I will add to the dict all the transcript information. keys will be (refseq, ensembl)
        Values will be the transcript info
        1- Taking all refseq transcripts 
        2- Take all ensembl transcript that were not in refseq collection
        3- give the conversion
        """
        return self.parser()

