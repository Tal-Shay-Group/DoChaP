import sys
import os
import copy
import time
import pandas as pd

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
        """Collect data (call director) for a single builder (attrName)"""
        self.director.setBuilder(self.__getattribute__(attrName))
        self.director.collectFromSource(download)
        print("{} data - collected!".format(attrName))

    def collectAll(self, download=False, withEns=True):
        """Collect data from all builders (using CollectSingle)"""
        BuildersList = ['refseq', 'idConv']
        if withEns:
            BuildersList.append('ensembl')
        for builder in BuildersList:
            self.CollectSingle(builder, download)
        print("--------------------------------")
        print("Data collection - COMPLETED!")
        if withEns:
            self.AllSourcesData()
        else:
            self.Transcripts = self.refseq.Transcripts
            self.Proteins = self.refseq.Proteins
            self.Genes = self.refseq.Genes
            self.Domains = self.refseq.Domains

    def AllSourcesData(self):
        """Combine the Transcrips, Gene, Protein, Domains data from refseq and ensembl"""
        print("Merging Transcript, Gene, Protein Data from Sources")
        # recombine = {}
        # ensembls = set()
        writtenIDs = set()
        genesIDs = set()
        for refT, record in self.refseq.Transcripts.items():
            if refT[1] == "R":  # only protein coding
                continue
            ensT = self.idConv.findConversion(refT, transcript=True)
            if record.protein_refseq is None or record.protein_refseq == '-':
                record.protein_refseq = self.refseq.trans2pro.get(refT, None)
            refP = record.protein_refseq
            ensP = self.idConv.findConversion(refP, protein=True)
            if refP is None or refP not in self.refseq.Proteins:  # if no matching protein - ignore the transcript
                continue
            ensPflag = ensP in self.ensembl.Proteins
            ensTflag = ensT in self.ensembl.Transcripts
            if not ensTflag and ensPflag:
                tempensT = self.ensembl.pro2trans[ensP]
                if ensT is None:
                    record.ensembl = tempensT
                ensT = tempensT
            elif ensTflag and not ensPflag:
                ensP = self.ensembl.trans2pro[ensT]

            refG = record.gene_GeneID
            ensG = self.idConv.findConversion(refG, gene=True)

            # add gene to dict
            if refG not in self.Genes:
                self.Genes[refG] = self.refseq.Genes[refG].mergeGenes(self.ensembl.Genes.get(ensG, ensG))
                genesIDs.add(refG)
                if ensG is not None:
                    genesIDs.add(ensG)

            if ensP in self.ensembl.Proteins and abs(int(self.refseq.Proteins[refP].length) - int(self.ensembl.Proteins[
                                                                                                      ensP].length)) <= 1:  # if the diff between protein length is smaller than 1- ignore
                self.mismatches_merged.append((ensP, refP,))
                self.Transcripts[refT] = self.idConv.FillInMissingsTranscript(record)
                self.Proteins[refP] = self.idConv.FillInMissingProteins(self.refseq.Proteins[refP])
                self.Proteins[refP].mergeDescription(self.ensembl.Proteins[ensP])
                self.Domains[refP] = self.CompMergeDomainLists(self.refseq.Domains.get(refP, []),
                                                               self.ensembl.Domains.get(ensP, []))
                writtenIDs.add(ensT)
                writtenIDs.add(refT)
                # if refG not in self.Genes:
                #     self.Genes[refG] = self.refseq.Genes[refG].mergeGenes(self.ensembl.Genes.get(ensG, ensG))
                #     genesIDs.add(refG)
                #     if ensG is not None:
                #         genesIDs.add(ensG)
            else:  # separate the records
                # refseq records
                self.Transcripts[refT] = self.refseq.Transcripts[refT]
                self.Transcripts[refT].gene_ensembl = ensG
                self.Proteins[refP] = self.refseq.Proteins[refP]
                self.Domains[refP] = self.refseq.Domains.get(refP, [])
                writtenIDs.add(refT)
                # if refG not in self.Genes:
                #     self.Genes[refG] = self.refseq.Genes[refG].mergeGenes(self.ensembl.Genes.get(ensG, ensG))
                #     genesIDs.add(refG)
                #     if ensG is not None:
                #         genesIDs.add(ensG)
                # ensembl records
                if ensP in self.ensembl.Proteins:
                    self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                    if ensG != self.Transcripts[ensT].gene_ensembl:
                        ensG = self.Transcripts[ensT].gene_ensembl
                        refG = self.idConv.findConversion(ensG, gene=True)
                    self.Transcripts[ensT].gene_GeneID = refG
                    self.Proteins[ensP] = self.ensembl.Proteins[ensP]
                    self.Domains[ensP] = self.ensembl.Domains.get(ensP, [])
                    self.mismatches_sep.append((ensP, refP,))
                    writtenIDs.add(ensT)
                    if refG is None:
                        self.Genes[ensG] = self.ensembl.Genes[ensG]
                        genesIDs.add(ensG)
                    elif refG not in self.Genes:
                        "here!!"
                        self.Genes[refG] = self.ensembl.Genes[ensG].mergeGenes(self.refseq.Genes.get(refG, refG))
                        genesIDs.add(refG)
                        if ensG is not None:
                            genesIDs.add(ensG)
                elif ensT not in self.ensembl.Transcripts:
                    self.Transcripts[refT] = self.idConv.FillInMissingsTranscript(record)
                    self.Proteins[refP] = self.idConv.FillInMissingProteins(self.refseq.Proteins[refP])
        # ~~~~ End of RefSeq Loop ~~~~~

        for ensT, record in self.ensembl.Transcripts.items():
            if ensT not in writtenIDs:
                ensP = record.protein_ensembl
                refT = self.idConv.findConversion(ensT, transcript=True)
                if ensP is None or ensP not in self.ensembl.Proteins or (refT is not None and refT[1] == "R"):
                    continue
                self.Transcripts[ensT] = self.idConv.FillInMissingsTranscript(record)
                # self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                # self.Proteins[ensP] = self.ensembl.Proteins[ensP]
                refP = record.protein_refseq
                self.Proteins[ensP] = self.idConv.FillInMissingProteins(self.ensembl.Proteins[ensP])
                self.Proteins[ensP].mergeDescription(self.refseq.Proteins.get(refP, None))
                self.Domains[ensP] = self.CompMergeDomainLists(self.refseq.Domains.get(refP, []),
                                                               self.ensembl.Domains.get(ensP, []))
                ensG = self.Transcripts[ensT].gene_ensembl
                refG = self.Transcripts[ensT].gene_GeneID
                if refG in self.Genes:
                    if ensG == self.idConv.findConversion(refG, gene=True) or self.idConv.findConversion(refG,
                                                                                                         gene=True) is None:
                        self.Genes[refG].ensembl = ensG if self.Genes[refG].ensembl is None else self.Genes[
                            refG].ensembl
                        genesIDs.add(ensG)
                    elif ensG not in genesIDs:
                        self.Genes[ensG] = self.ensembl.Genes[ensG]
                        self.Transcripts[ensT].gene_GeneID = None
                        genesIDs.add(ensG)
                elif ensG not in genesIDs:
                    if refG is None:
                        self.Genes[ensG] = self.ensembl.Genes[ensG]
                        genesIDs.add(ensG)
                    else:
                        self.ensembl.Genes[ensG].gene_GeneID = refG
                        self.Genes[refG] = self.ensembl.Genes[ensG].mergeGenes(self.refseq.Genes.get(refG, refG))
                        genesIDs.add(ensG)
                        genesIDs.add(refG)
        # ~~~~~ End of Ensmebl Loop ~~~~~

    def CompMergeDomainLists(self, doms1, doms2):
        if len(doms1) == 0 or doms1 is None:
            return doms2
        elif len(doms2) == 0 or doms2 is None:
            return doms1
        finalList = list(doms1)
        added_index = []
        for dom in doms1:
            for i in range(len(doms2)):
                refDom = doms2[i]
                if i not in added_index and dom != refDom:
                    finalList.append(refDom)
                    added_index.append(i)
        return tuple(finalList)


if __name__ == '__main__':
    start_time = time.time()
    species = "M_musculus"
    col = Collector(species)
    col.collectAll()
    print("--- %s seconds ---" % (time.time() - start_time))
