from OOP_project.Director import Director
from OOP_project.UcscBuilder import UcscBuilder
from OOP_project.ffBuilder import ffBuilder
from OOP_project.IDconverterBuilder import ConverterBuilder
from OOP_project.gffRefseqBuilder import RefseqBuilder
from OOP_project.gffEnsemblBuilder import EnsemblBuilder


class Collector:

    def __init__(self, species):
        self.species = species
        self.director = Director()
        self.refseq = RefseqBuilder(self.species)
        self.ensembl = EnsemblBuilder(self.species)
        # self.ucsc = UcscBuilder(self.species)
        # self.ff = ffBuilder(self.species)
        self.idConv = ConverterBuilder(self.species)
        self.Transcripts = None
        self.Genes = None
        self.Domains = None
        self.Proteins = None

    def CollectSingle(self, attrName, download=False):
        self.director.setBuilder(self.__getattribute__(attrName))
        self.director.collectFromSource(download)

    def collectAll(self, completeMissings=True, download=False):
        # for builder in ['ucsc', 'idConv', 'ff']:
        for builder in ['refseq', 'ensembl', 'idConv']:
            self.CollectSingle(builder, download)
        if completeMissings:
            self.MergeTranscripts()
            # self.CompleteProteinData()
            # self.CompleteGenesData()
        else:
            self.Transcripts = self.refseq.Transcripts
        self.Proteins = self.refseq.Proteins
        self.Genes = self.refseq.Genes
        self.Domains = self.refseq.Domains

    def MergeTranscripts(self):
        recombine = {}
        ensembls = set()
        refseqs = set()
        for idt, record in self.refseq.Transcripts.items():
            if idt[1] == "R":
                continue
            newT = self.idConv.FillInMissingsTranscript(record)
            # if newT.gene_GeneID is None:
            #    newT.gene_GeneID = [self.ff.genes[newT.idNoVersion()].GeneID if
            #                        newT.idNoVersion() in self.ff.genes else
            #                        newT.gene_GeneID][0]
            if newT.protein_refseq is None or '-':
                newT.protein_refseq = self.refseq.trans2pro.get(newT.refseq, None)
            recombine[newT.refseq] = newT
            ensembls.add(newT.ensembl)
            refseqs.add(newT.refseq)
        for idt, record in self.ensembl.Transcripts.items():
            if idt in ensembls:
                continue
            newT = self.idConv.FillInMissingsTranscript(record)
            newT.protein_ensembl = self.idConv.idNov.get(newT.protein_ensembl, newT.protein_ensembl)
            if (newT.refseq is not None and newT.refseq[1] == "R") or \
                    newT.protein_refseq == '-' or newT.protein_ensembl == '-':
                continue
            elif newT.refseq is None or newT.refseq not in refseqs:
                recombine[newT.ensembl] = newT
            elif newT.refseq in refseqs:
                print(newT.refseq)
                recombine[newT.refseq] = recombine[newT.refseq].mergeTranscripts(newT)
            else:
                raise ValueError(
                    "Transcript fails to match any of the statements : {}, {}".format(newT.refseq, newT.ensembl))
        self.Transcripts = recombine

    def CompleteProteinData(self):
        recombine = {}
        for pid, protein in self.ff.proteins.items():
            if protein.ensembl is None:
                newP = protein
                newP.ensembl = self.idConv.findConversion(newP.refseq, protein=True)
            else:
                newP = protein
            recombine[pid] = newP
        ##add for ensembl
        self.Proteins = recombine

    def CompleteGenesData(self):
        recombine = {}
        for gid, gene in self.ff.genes.items():
            if gene.ensembl is None:
                newG = gene
                newG.ensembl = self.idConv.findConversion(newG.GeneID, gene=True)
            else:
                newG = gene
            recombine[gid] = newG
        ### add for ensembl
        self.Genes = recombine
