import sys
import os
import copy
import time

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
        self.Transcripts = {}
        self.Genes = {}
        self.Domains = {}
        self.Proteins = {}
        self.mismatches_sep = []
        self.mismatches_merged = []

    def CollectSingle(self, attrName, download=False):
        self.director.setBuilder(self.__getattribute__(attrName))
        self.director.collectFromSource(download)
        print("{} data - collected!".format(attrName))

    def collectAll(self, download=False, withEns=True):
        BuildersList = ['refseq', 'idConv']
        if withEns:
            BuildersList.append('ensembl')
        for builder in BuildersList:
            self.CollectSingle(builder, download)
        print("--------------------------------")
        print("Data collection - COMPLETED!")
        if withEns:
            self.AllSourcesTranscripts()
            # self.AllSourcesProteinsDomains(withEns=withEns)
            # self.AllSourcesGenes(withEns=withEns)
            # self.AllSourcesDomains(withEns=withEns)
        else:
            self.Transcripts = self.refseq.Transcripts
            self.Proteins = self.refseq.Proteins
            self.Genes = self.refseq.Genes
            self.Domains = self.refseq.Domains

    def AllSourcesTranscripts(self):
        print("Merging Transcripts Data from Sources")
        # recombine = {}
        # ensembls = set()
        writtenIDs = set()
        for refT, record in self.refseq.Transcripts.items():
            if refT[1] == "R":
                continue
            ensT = col.idConv.findConversion(refT, transcript=True)
            if record.protein_refseq is None or '-':
                record.protein_refseq = self.refseq.trans2pro.get(refT, None)
            refP = record.protein_refseq
            ensP = col.idConv.findConversion(refP, protein=True)
            if refP is None:
                continue
            if ensP in col.ensembl.Proteins.keys() and \
                    abs(int(col.refseq.Proteins[refP].length) - int(col.ensembl.Proteins[
                                                                        ensP].length)) <= 1:  # if the diff between protein length is smaller than 1- ignore
                self.mismatches_merged.append((ensP, refP,))
                self.Transcripts[refT] = self.idConv.FillInMissingsTranscript(record)
                refG = self.Transcripts[refT].gene_GeneID
                ensG = col.idConv.findConversion(refG, gene=True)
                self.Genes[refG] = col.refseq.Genes[refG].mergeGenes(col.ensembl.Genes[ensG])
                self.Proteins[refP] = self.idConv.FillInMissingProteins(col.refseq.Proteins[refP])
                self.Domains[refP] = self.CompMergeDomainLists(self.refseq.Domains.get(refP, []),
                                                               self.ensembl.Domains.get(ensP, []))
            else:  # else - separate the records
                # refseq records
                self.Transcripts[refT] = self.refseq.Transcripts[refT]
                self.Proteins[refP] = self.refseq.Proteins[refP]
                self.Genes[refG] = self.refseq.Genes[refG]
                self.Domains[refP] = self.refseq.Domains.get(refP, [])
                if ensP in col.ensembl.Proteins:  # ensembl records
                    self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                    self.Proteins[ensP] = self.ensembl.Proteins[ensP]
                    self.Genes[ensG] = self.ensembl.Genes[ensG]
                    self.Domains[ensP] = self.ensembl.Domains.get(ensP, [])

                    self.mismatches_sep.append((ensP, refP,))

            writtenIDs.add(ensT)
            writtenIDs.add(refT)

        for ensT, record in col.ensembl.Transcripts.Keys():
            if ensT not in writtenIDs:
                ensP = record.protein_ensembl
                if ensP is None:
                    continue
                ensG = record.gene_ensembl
                self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                self.Proteins[ensP] = self.ensembl.Proteins[ensP]
                self.Genes[ensG] = self.ensembl.Genes[ensG]
                self.Domains[ensP] = self.ensembl.Domains.get(ensP, [])

    #         newT = record
    #         if newT.protein_refseq is None or '-':
    #             newT.protein_refseq = self.refseq.trans2pro.get(newT.refseq, None)
    #
    #
    #         newT = copy.deepcopy(record)
    #         newT = self.idConv.FillInMissingsTranscript(newT)
    #
    #         recombine[newT.refseq] = newT
    #         ensembls.add(newT.ensembl)
    #         refseqs.add(newT.refseq)
    #     if not withEns:
    #         self.Transcripts = recombine
    #         return
    #     for idt, record in self.ensembl.Transcripts.items():
    #         if idt in ensembls:
    #             continue
    #         newT = copy.deepcopy(record)
    #         newT = self.idConv.FillInMissingsTranscript(newT)
    #         newT.protein_ensembl = self.idConv.idNov.get(newT.protein_ensembl, newT.protein_ensembl)
    #         if (newT.refseq is not None and newT.refseq[1] == "R") or \
    #                 newT.protein_refseq == '-' or newT.protein_ensembl == '-':
    #             continue
    #         elif newT.refseq is not None and newT.refseq.startswith("mito-") and newT.refseq in refseqs:
    #             recombine[newT.refseq] = newT
    #         elif newT.refseq is None or newT.refseq not in refseqs:
    #             recombine[newT.ensembl] = newT
    #         elif newT.refseq in refseqs:
    #             recombine[newT.refseq] = recombine[newT.refseq].mergeTranscripts(newT)
    #         else:
    #             raise ValueError(
    #                 "Transcript fails to match any of the statements : {}, {}".format(newT.refseq, newT.ensembl))
    #     self.Transcripts = recombine
    #
    # def AllSourcesProteinsDomains(self, withEns=True):
    #     print("Merging Proteins and Domains Data from Sources")
    #     recombine = {}
    #     ensembls = set()
    #     refseqs = set()
    #     for pid, protein in self.refseq.Proteins.items():
    #         newP = copy.deepcopy(protein)
    #         newP = self.idConv.FillInMissingProteins(newP)
    #         ensembls.add(newP.ensembl)
    #         refseqs.add(newP.refseq)
    #         recombine[pid] = newP
    #     self.Domains = self.refseq.Domains
    #     if not withEns:
    #         self.Proteins = recombine
    #         return
    #     else:
    #         for ensP, protein in self.ensembl.Proteins.items():
    #             newP = copy.deepcopy(protein)
    #             newP = self.idConv.FillInMissingProteins(newP)
    #             if newP.ensembl in ensembls:
    #                 refP = newP.refseq
    #                 if abs(int(recombine[refP].length) - int(newP.length)) <= 1: # if the diff between protein length is smaller than 1- ignore
    #                     newP.length = recombine[refP].length
    #                     self.mismatches_merged.append((newP.ensembl, refP,))
    #                     self.Domains[refP] = self.CompMergeDomainLists(self.Domains.get(refP, []), self.ensembl.Domains.get(ensP, []))
    #                 else: # else - separate the records
    #                     refT = self.idConv.TranscriptProtein(refP)
    #                     ensT = self.idConv.TranscriptProtein(newP.ensembl)
    #                     if refT in self.Transcripts:
    #                         self.Transcripts[refT] = self.refseq.Transcripts[refT]
    #                         self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
    #                     if refP in recombine:
    #                         recombine[refP] = self.refseq.Proteins[refP]
    #                     recombine[ensP] = protein
    #                     self.Domains[ensP] = self.ensembl.Domains[ensP]
    #                     self.mismatches_sep.append((protein.ensembl, refP,))
    #                 # print("inconsistency between refseq and ensembl length, protein: {}, {}".format(protein.ensembl,refs))
    #             else:
    #                 if refP is not None and refP in refseqs:
    #                     if recombine[refP].ensembl is None:
    #                         recombine[refP].ensembl = newP.ensembl
    #                     self.Domains[refP] = self.CompMergeDomainLists(self.Domains.get(refP, []),
    #                                                                    self.ensembl.Domains.get(ensP, []))
    #                 else:
    #                     recombine[ensP] = newP
    #                     self.Domains[ensP] = self.ensembl.Domains[ensP]
    #         self.Proteins = recombine
    #
    # def AllSourcesGenes(self, withEns=True):
    #     print("Merging Genes Data from Sources")
    #     recombine = {}
    #     ensembls = set()
    #     refseqs = set()
    #     for gid, gene in self.refseq.Genes.items():
    #         if gene.ensembl is None:
    #             newG = copy.deepcopy(gene)
    #             newG.ensembl = self.idConv.findConversion(newG.GeneID, gene=True)
    #         else:
    #             newG = copy.deepcopy(gene)
    #         recombine[gid] = newG
    #         ensembls.add(newG.ensembl)
    #         refseqs.add(newG.GeneID)
    #     if not withEns:
    #         self.Genes = recombine
    #         return
    #     else:
    #         for gid, gene in self.ensembl.Genes.items():
    #             newG = copy.deepcopy(gene)
    #             if newG.GeneID is None:
    #                 newG.GeneID = self.idConv.findConversion(newG.ensembl, gene=True)
    #             if newG.GeneID in recombine.keys():
    #                 recombine[newG.GeneID] = recombine[newG.GeneID].mergeGenes(newG)
    #             elif gid in recombine.keys():
    #                 recombine[newG] = recombine[gid].mergeGenes(newG)
    #             else:
    #                 recombine[newG] = gene
    #     self.Genes = recombine

    # def AllSourcesDomains(self, withEns=True):
    #     print("Merging Domains Data from Sources")
    #     recombine = self.refseq.Domains
    #     if not withEns:
    #         self.Domains = recombine
    #         return
    #     for pid, domList in self.ensembl.Domains.items():
    #         refP = self.idConv.findConversion(pid, protein=True)
    #         if pid in self.Proteins:
    #             recombine[pid] = domList
    #         elif refP in self.Proteins:
    #             if refP in recombine:
    #                 currentDomains = recombine[refP]
    #                 for dom in domList:
    #                     for refDom in currentDomains:
    #                         if dom.extID == refDom.extID and dom.aaStart == refDom.aaStart and dom.aaEnd == refDom.aaEnd:
    #                             continue
    #                         else:
    #                             recombine[refP] = recombine[refP] + (dom,)
    #             else:
    #                 recombine[refP] = domList
    #     self.Domains = recombine

    def CompMergeDomainLists(self, doms1, doms2):
        if len(doms1) == 0:
            return doms2
        elif len(doms2) == 0:
            return doms1
        finalList = list(doms1)
        for dom in doms1:
            for refDom in doms2:
                if not dom.__eq__(refDom):
                    finalList.append(refDom)
        return tuple(finalList)


if __name__ == '__main__':
    start_time = time.time()
    species = "M_musculus"
    col = Collector(species)
    col.collectAll()
    print("--- %s seconds ---" % (time.time() - start_time))
