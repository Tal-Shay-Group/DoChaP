# import ftplib
# import gzip
import os
import sys

sys.path.append(os.getcwd())
from ftpDownload import ftpDownload
from recordTypes import Transcript
from Director import SourceBuilder


class ConverterBuilder(SourceBuilder):
    """
    Download and parse conversions from refseq to ensembl
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
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

    def downloader(self):
        ftp_address = 'ftp.ncbi.nlm.nih.gov'
        ftp_path = '/gene/DATA/'
        filename = 'gene2ensembl'
        files2down = [[filename, filename + ".txt"]]
        down = ftpDownload(species=None, ftp_adress=ftp_address, ftp_path=ftp_path, savePath=self.savePath,
                           files2Download=files2down)
        down.Download()

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
                    # ll = [None if it == "-" else it for it in ll]
                    self.geneCon[ll[1]] = self.geneCon.get(ll[1], ll[2])
                    self.geneCon[ll[2]] = self.geneCon.get(ll[2], ll[1])
                    if [i for i in range(len(ll)) if ll[i] == "-"] == [3, 4]:
                        # mito genes has no transcript id
                        ll[3] = "mito-" + ll[1]
                        ll[4] = "mito-" + ll[2]
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
            newT.ensembl = self.findConversion(newT.refseq, transcript=True) \
                if newT.ensembl is None else newT.ensembl
            geneID = self.GeneTrans(newT.refseq)
            newT.gene_GeneID = geneID if geneID is None else newT.gene_GeneID
            newT.gene_ensembl = self.findConversion(newT.gene_GeneID, gene=True) \
                if newT.gene_ensembl is None else newT.gene_ensembl
            newT.protein_refseq = self.TranscriptProtein(newT.refseq) \
                if newT.protein_refseq is None else newT.protein_refseq
            newT.protein_ensembl = self.findConversion(newT.protein_refseq, protein=True) \
                if newT.protein_ensembl is None else newT.protein_ensembl
        elif newT.ensembl is not None:
            newT.refseq = self.findConversion(newT.ensembl, transcript=True) \
                if newT.refseq is None else newT.refseq
            newT.gene_ensembl = self.GeneTrans(newT.ensembl) \
                if newT.gene_ensembl is None else newT.gene_ensembl
            newT.gene_GeneID = self.findConversion(newT.gene_ensembl, gene=True) \
                if newT.gene_GeneID is None else newT.gene_GeneID
            if newT.refseq is None and newT.gene_GeneID is not None and newT.chrom == "MT":  # mitochondrial genes has no refseq id
                tempRefseq = "mito-" + newT.gene_GeneID
                if tempRefseq in self.transcriptCon:
                    newT.refseq = tempRefseq
                    self.transcriptCon[tempRefseq] = newT.ensembl
                    self.transcriptCon[newT.ensembl] = tempRefseq
                    if "mito-" + newT.gene_ensembl in self.t2g:  # replace wrong transcript in the IDconv data
                        self.t2g[newT.ensembl] = self.t2g["mito-" + newT.gene_ensembl]
            newT.protein_ensembl = self.TranscriptProtein(newT.ensembl) \
                if newT.protein_ensembl is None else newT.protein_ensembl
            newT.protein_refseq = self.findConversion(newT.protein_ensembl, protein=True) \
                if newT.protein_refseq is None else newT.protein_refseq
        return newT

    def FillInMissingProteins(self, proteinRec):
        if proteinRec.refseq is None:
            proteinRec.refseq = self.findConversion(proteinRec.ensembl, protein=True)
        elif proteinRec.ensembl is None:
            proteinRec.ensembl = self.findConversion(proteinRec.refseq, protein=True)
        return proteinRec
