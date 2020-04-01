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
                    #ll = [None if it == "-" else it for it in ll]
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
                    for i in range(1, 7):
                        self.idNov[ll[i].split(".")[0]] = ll[i]

    def findConversion(self, inp, transcript=False, gene=False, protein=False):
        if inp is None:
            return None
        elif transcript:
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
            return self.proteinCon.get(self.t2p[self.transcriptCon[inp]], None)
        elif self.proteinCon.get(inp, None) in self.p2t.keys():
            return self.transcriptCon.get(self.p2t[self.proteinCon[inp]], None)
        else:
            return None

    def GeneTrans(self, inp):
        return self.t2g.get(inp, self.t2g.get(self.idNov.get(inp.split(".")[0], None), None))

    def FillInMissingsTranscript(self, transcript):
        newT = transcript
        if newT.refseq is not None:
            newT.ensembl = self.findConversion(newT.refseq, transcript=True)\
                if newT.ensembl is None else newT.ensembl
            newT.gene_GeneID = self.GeneTrans(newT.refseq)\
                if newT.gene_GeneID is None else newT.gene_GeneID
            newT.gene_ensembl = self.findConversion(newT.gene_GeneID, gene=True)\
                if newT.gene_ensembl is None else newT.gene_ensembl
            newT.protein_refseq = self.TranscriptProtein(newT.refseq)\
                if newT.protein_refseq is None else newT.protein_refseq
            newT.protein_ensembl = self.findConversion(newT.protein_refseq, protein=True)\
                if newT.protein_ensembl is None else newT.protein_ensembl
        elif newT.ensembl is not None:
            newT.refseq = self.findConversion(newT.ensembl, transcript=True)\
                                 if newT.refseq is None else newT.refseq
            newT.gene_ensembl = self.GeneTrans(newT.ensembl)\
                if newT.gene_ensembl is None else newT.gene_ensembl
            newT.gene_GeneID = self.findConversion(newT.gene_ensembl, gene=True)\
                if newT.gene_GeneID is None else newT.gene_GeneID
            newT.protein_ensembl = self.TranscriptProtein(newT.ensembl)\
                if newT.protein_ensembl is None else newT.protein_ensembl
            newT.protein_refseq = self.findConversion(newT.protein_ensembl, protein=True)\
                if newT.protein_refseq is None else newT.protein_refseq
        return newT
