import ftplib
import gzip
import os
from OOP_project.recordTypes import Transcript
from OOP_project.Director import SourceBuilder


class ConverterBuilder(SourceBuilder):
    """
    Download and parse conversions from refseq to ensembl
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        self.ftp_address = 'ftp.ncbi.nlm.nih.gov'
        self.savePath = os.getcwd() + '/data/'
        taxIDdict = {'M_musculus': 10090, 'H_sapiens': 9606, 'R_norvegicus': 10116, 'D_rerio': 7955,
                     'X_tropicalis': 8364}
        self.taxID = taxIDdict[self.species]
        self.geneCon = {}
        self.transcriptCon = {}
        self.proteinCon = {}
        self.t2p = {}
        self.p2t = {}
        self.t2g = {}
        self.idNov = {}

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
                    self.t2p[ll[3]] = ll[5]
                    self.p2t[ll[5]] = ll[3]
                    self.t2g[ll[3]] = ll[1]
                    self.t2g[ll[4]] = ll[2]
                    for i in range(1,7):
                        self.idNov[ll[i].split(".")[0]] = ll[i]

    def findConversion(self, inp, transcript=False, gene=False, protein=False):
        if transcript:
            return self.transcriptCon.get(inp, self.transcriptCon.get(self.idNov.get(inp.split(".")[0], None), None))
        elif gene:
            return self.geneCon.get(inp, self.geneCon.get(self.idNov.get(inp.split(".")[0], None), None))
        elif protein:
            return self.proteinCon.get(inp, self.proteinCon.get(self.idNov.get(inp.split(".")[0], None), None))
        else:
            raise ValueError('Must declare input type transcript/gene/protein=True')

    def TranscriptProtein(self, inp):
        if inp in self.t2p.keys():
            return self.t2p[inp]
        elif inp in self.p2t.keys():
            return self.p2t[inp]
        elif self.transcriptCon.get(inp, None) in self.t2p.keys():
            return self.t2p[self.transcriptCon[inp]]
        elif self.proteinCon.get(inp, None) in self.p2t.keys():
            return self.p2t[self.proteinCon[inp]]
        else:
            return None
