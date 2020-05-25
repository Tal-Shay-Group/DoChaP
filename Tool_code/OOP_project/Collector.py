import sys
import os

sys.path.append(os.getcwd())
from Director import Director
from IDconverterBuilder import ConverterBuilder
from gffRefseqBuilder import RefseqBuilder
from gffEnsemblBuilder import EnsemblBuilder


class Collector:

    def __init__(self, species):
        self.species = species
        self.director = Director()
        self.refseq = RefseqBuilder(self.species)
        self.ensembl = EnsemblBuilder(self.species)
        self.idConv = ConverterBuilder(self.species)
        self.Transcripts = None
        self.Genes = None
        self.Domains = None
        self.Proteins = None
        self.mismatches_sep =[]
        self.mismatches_merged = []

    def CollectSingle(self, attrName, download=False):
        self.director.setBuilder(self.__getattribute__(attrName))
        self.director.collectFromSource(download)

    def collectAll(self, download=False, withEns=True):
        BuildersList = ['refseq', 'idConv']
        if withEns:
            BuildersList.append('ensembl')
        for builder in BuildersList:
            self.CollectSingle(builder, download)
        if withEns:
            self.MergeTranscripts(withEns=withEns)
            self.CompleteProteinData(withEns=withEns)
            self.CompleteGenesData(withEns=withEns)
        else:
            self.Transcripts = self.refseq.Transcripts
            self.Proteins = self.refseq.Proteins
            self.Genes = self.refseq.Genes
        self.Domains = self.refseq.Domains

    def MergeTranscripts(self, withEns=True):
        recombine = {}
        ensembls = set()
        refseqs = set()
        for idt, record in self.refseq.Transcripts.items():
            if idt[1] == "R":
                continue
            newT = self.idConv.FillInMissingsTranscript(record)
            if newT.protein_refseq is None or '-':
                newT.protein_refseq = self.refseq.trans2pro.get(newT.refseq, None)
            recombine[newT.refseq] = newT
            ensembls.add(newT.ensembl)
            refseqs.add(newT.refseq)
        if not withEns:
            self.Transcripts = recombine
            return
        for idt, record in self.ensembl.Transcripts.items():
            if idt in ensembls:
                continue
            newT = self.idConv.FillInMissingsTranscript(record)
            newT.protein_ensembl = self.idConv.idNov.get(newT.protein_ensembl, newT.protein_ensembl)
            if (newT.refseq is not None and newT.refseq[1] == "R") or \
                    newT.protein_refseq == '-' or newT.protein_ensembl == '-':
                continue
            elif newT.refseq is not None and newT.refseq.startswith("mito-") and newT.refseq in refseqs:
                recombine[newT.refseq] = newT
            elif newT.refseq is None or newT.refseq not in refseqs:
                recombine[newT.ensembl] = newT
            elif newT.refseq in refseqs:
                recombine[newT.refseq] = recombine[newT.refseq].mergeTranscripts(newT)
            else:
                raise ValueError(
                    "Transcript fails to match any of the statements : {}, {}".format(newT.refseq, newT.ensembl))
        self.Transcripts = recombine

    def CompleteProteinData(self, withEns=True):
        recombine = {}
        ensembls = set()
        refseqs = set()
        for pid, protein in self.refseq.Proteins.items():
            newP = protein
            newP = self.idConv.FillInMissingProteins(newP)
            ensembls.add(newP.ensembl)
            refseqs.add(newP.refseq)
            recombine[pid] = newP
        if not withEns:
            self.Proteins = recombine
            return
        else:
            for pid, protein in self.ensembl.Proteins.items():
                if protein.ensembl in ensembls:
                    refs = self.idConv.proteinCon[protein.ensembl]
                    if recombine[refs].length != protein.length:
                        # raise ValueError("inconsistency between refseq and ensembl length, protein: {}, {}".format(protein.ensembl,refs))
                        if abs(int(recombine[refs].length) - int(protein.length)) <= 1:
                            protein.length = recombine[refs].length
                            self.mismatches_merged.append((protein.ensembl, refs,))
                        else:
                            refT = self.idConv.TranscriptProtein(refs)
                            ensT = self.idConv.TranscriptProtein(protein.ensembl)
                            if refT in self.Transcripts:
                                self.Transcripts[refT].ensembl = None
                                self.Transcripts[refT].protein_ensembl = None
                                self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                            if refs in recombine:
                                recombine[refs].ensembl = None
                                recombine[refs].protein_ensembl = None
                            recombine[pid] = protein
                            self.mismatches_sep.append((protein.ensembl, refs,))
                        # print("inconsistency between refseq and ensembl length, protein: {}, {}".format(protein.ensembl,refs))
                else:
                    newP = protein
                    newP = self.idConv.FillInMissingProteins(newP)
                    if newP.refseq is not None and newP.refseq in refseqs:
                        if recombine[newP.refseq].ensembl is None:
                            recombine[newP.refseq].ensembl = newP.ensembl
                    else:
                        recombine[newP.ensembl] = newP
            self.Proteins = recombine

    def CompleteGenesData(self, withEns=True):
        recombine = {}
        ensembls = set()
        refseqs = set()
        for gid, gene in self.refseq.Genes.items():
            if gene.ensembl is None:
                newG = gene
                newG.ensembl = self.idConv.findConversion(newG.GeneID, gene=True)
            else:
                newG = gene
            recombine[gid] = newG
            ensembls.add(newG.ensembl)
            refseqs.add(newG.GeneID)
        if not withEns:
            self.Genes = recombine
            return
        else:
            for gid, gene in self.ensembl.Genes.items():
                if gene.GeneID is None:
                    gene.GeneID = self.idConv.findConversion(gene.ensembl, gene=True)
                if gene.GeneID in recombine.keys():
                    recombine[gene.GeneID] = recombine[gene.GeneID].mergeGenes(gene)
                elif gid in recombine.keys():
                    recombine[gid] = recombine[gid].mergeGenes(gene)
                else:
                    recombine[gid] = gene
        self.Genes = recombine

if __name__ == '__main__':
    for sp in ["H_sapiens", "D_rerio", "X_tropicalis", "R_norvegicus"]:
        col = Collector(sp)
        col.collectAll(download=True, withEns=True)
