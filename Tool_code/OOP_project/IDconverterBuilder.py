import ftplib
import gzip
import os
from recordTypes import *

from Director import SourceBuilder


class ConverterBuilder(SourceBuilder):
    """
    Download and parse conversions from refseq to ensembl
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        self.ftp_address = 'ftp.ncbi.nlm.nih.gov'
        self.savePath = os.getcwd() + '/data/'
        taxIDdict = {'M_musculus': 10090, 'H_sapiens': 9606, 'R_norvegicus': 10116, 'D_rerio': 7955, 'X_tropicalis': 8364}
        self.taxID = taxIDdict[self.species]
        self.geneCon = {}
        self.transcriptCon = {}
        self.proteinCon = {}

    def downloader(self, username='anonymous', pswd='example@post.bgu.ac.il'):
        print('connecting to: ' + self.ftp_address + '...')
        ftp = ftplib.FTP(self.ftp_address)
        print('logging in...')
        ftp.login(user=username, passwd=pswd)
        ftp_path = '/gene/DATA/'
        ftp.cwd(ftp_path)
        print('downloading files to : ' + self.savePath)
        os.makedirs(self.savePath, exist_ok=True)
        filename = 'gene2ensembl'
        print('downloading: ', filename, '...')
        ftp.sendcmd("TYPE i")
        # size = ftp.size(file[0])
        with open(self.savePath + filename + '.txt.gz', 'wb') as f:
            def callback(chunk):
                f.write(chunk)

            ftp.retrbinary("RETR " + filename + '.gz', callback)
        print('extracting...')
        inp = gzip.GzipFile(self.savePath + filename + '.txt.gz', 'rb')
        s = inp.read()
        inp.close()
        with open(self.savePath + filename + '.txt', 'wb') as f_out:
            f_out.write(s)
        print('removing compressed file...')
        os.remove(self.savePath + filename + '.txt.gz')

    def parser(self):
        """
        This function uses the table gene2ensembl from refseq database to create all connections
        between RefSeq and ENSEMBL for gene, transcript, protein
        Table columns: table columns:
        taxID;geneID;ENS_GeneID;refseq_transcript;ENS_transcript;refseq_protein;ENS_protein
        """
        with open(self.savePath + 'gene2ensembl.txt', 'r') as g2e:
            for line in g2e:
                ll = line.strip().split('\t')
                # print(ll)
                if ll[0] == str(self.taxID):
                    # print(ll[0])
                    self.geneCon[ll[1]] = self.geneCon.get(ll[1], ll[2])
                    self.geneCon[ll[2]] = self.geneCon.get(ll[2], ll[1])
                    self.transcriptCon[ll[3]] = ll[4]
                    self.transcriptCon[ll[4]] = ll[3]
                    self.proteinCon[ll[5]] = ll[6]
                    self.proteinCon[ll[6]] = ll[5]
        #return gene_con, trans_con, protein_con

    def findConversion(self, inp, transcript=False, gene=False, protein=False):
        if transcript:
            return self.transcriptCon[inp]
        elif gene:
            return self.geneCon[inp]
        elif protein:
            return self.proteinCon[inp]
        else:
            raise ValueError('Must declare input type transcript/gene/protein=True')