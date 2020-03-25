from Director import *
from ffBuilder import *
from UcscBuilder import *
import ensemblBuilder
import OrthologsBuilder
import IDconverterBuilder

from OOP_project.Director import Director
from OOP_project.UcscBuilder import UcscBuilder
from OOP_project.ffBuilder import ffBuilder
from OOP_project.IDconverterBuilder import ConverterBuilder


class Collector:

    def __init__(self, species):
        self.species = species
        self.director = Director()
        self.ucsc = UcscBuilder(self.species)
        self.ff = ffBuilder(self.species)
        self.idConv = ConverterBuilder(self.species)
        self.Transcripts = None
        self.Genes = None
        self.Domains = None
        self.Proteins = None

    def CollectSingle(self, attrName, download=False):
        self.director.setBuilder(self.__getattribute__(attrName))
        self.director.collectFromSource(download)

    def collectAll(self, completeMissings=True, download=False):
        for builder in ['ucsc', 'idConv', 'ff']:
            self.CollectSingle(builder, download)
        if completeMissings:
            self.CompleteTranscriptData()
            self.CompleteProteinData()
            self.CompleteGenesData()
        else:
            self.Transcripts = self.ucsc.combined
            self.Proteins = self.ff.proteins
            self.Genes = self.ff.genes
        self.Domains = self.ff.domains

    def CompleteTranscriptData(self):
        recombine = {}
        for idt, record in self.ucsc.refseq.items():
            if idt[1] == "R":
                continue
            newT = record
            if record.ensembl is None:
                newT.ensembl = self.idConv.findConversion(newT.refseq, transcript=True)
            if newT.protein_ensembl is None:
                if newT.prot_refseq is not None:
                    newT.protein_ensembl = self.idConv.findConversion(newT.prot_refseq, protein=True)
                elif newT.refseq in self.idConv.t2p:
                    newT.prot_refseq = self.idConv.TranscriptProtein(newT.refseq)
                    newT.protein_ensembl = self.idConv.TranscriptProtein(newT.ensembl)
                else:
                    newT.prot_refseq = [self.ff.trans2pro[newT.idNoVersion()] if
                                        newT.idNoVersion() in self.ff.trans2pro.keys() else
                                        newT.prot_refseq][0]
                    ### ADD FOR ENSEMBL!!!
            if newT.gene_GeneID is None:
                if newT.refseq in self.idConv.t2g or newT.idNoVersion() in self.idConv.idNov:
                    newT.gene_GeneID = self.idConv.t2g[newT.refseq]
                    newT.gene_ensembl = self.idConv.findConversion(newT.gene_GeneID, gene=True)
                else:
                    newT.gene_GeneID = [self.ff.genes[newT.idNoVersion()].GeneID if
                                        newT.idNoVersion() in self.ff.genes else
                                        newT.prot_refseq][0]
                    ### ADD FOR ENSEMBL!!!
            recombine[newT.refseq] = newT
        for idt, record in self.ucsc.ensembl.items():
            newT = record
            if newT.refseq is None:
                newT.refseq = self.idConv.findConversion(newT.ensembl, transcript=True)
            if newT.refseq is not None and newT.refseq[1] == "R":
                continue
            if newT.prot_refseq is None:
                if newT.protein_ensembl is not None:
                    newT.prot_refseq = self.idConv.findConversion(newT.protein_ensembl, protein=True)
                elif newT.protein_ensembl in self.idConv.t2p:
                    newT.prot_refseq = self.idConv.TranscriptProtein(newT.refseq)
                    newT.protein_ensembl = self.idConv.TranscriptProtein(newT.ensembl)
                else:
                    newT.prot_refseq = [self.ff.trans2pro[newT.idNoVersion()] if
                                        newT.idNoVersion() in self.ff.trans2pro.keys() else
                                        newT.prot_refseq][0]
                    ### ADD FOR ENSEMBL!!!
            if newT.gene_ensembl is None:
                if newT.refseq in self.idConv.t2g:
                    newT.gene_GeneID = self.idConv.t2g[newT.refseq]
                    newT.gene_ensembl = self.idConv.findConversion(newT.gene_GeneID, gene=True)
                else:
                    newT.gene_GeneID = [self.ff.genes[newT.idNoVersion()].GeneID if
                                        newT.idNoVersion() in self.ff.genes else
                                        newT.prot_refseq][0]
                    ### ADD FOR ENSEMBL!!!
            if newT.refseq in recombine.keys():
                recombine[newT.refseq] = recombine[newT.refseq].mergeTranscripts(newT)
            elif newT.refseq is not None:
                recombine[newT.refseq] = newT
            else:
                recombine[newT.ensembl] = newT
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
