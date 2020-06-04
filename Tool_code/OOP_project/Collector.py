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
        genesIDs = set()
        for refT, record in self.refseq.Transcripts.items():
            if refT[1] == "R":
                continue
            ensT = self.idConv.findConversion(refT, transcript=True)
            if record.protein_refseq is None or record.protein_refseq == '-':
                record.protein_refseq = self.refseq.trans2pro.get(refT, None)
            refP = record.protein_refseq
            ensP = self.idConv.findConversion(refP, protein=True)
            if refP is None or refP not in self.refseq.Proteins:
                continue
            if ensP in self.ensembl.Proteins.keys() and \
                    abs(int(self.refseq.Proteins[refP].length) - int(self.ensembl.Proteins[
                                                                         ensP].length)) <= 1:  # if the diff between protein length is smaller than 1- ignore
                self.mismatches_merged.append((ensP, refP,))
                self.Transcripts[refT] = self.idConv.FillInMissingsTranscript(record)
                refG = self.Transcripts[refT].gene_GeneID
                ensG = self.Transcripts[refT].gene_ensembl
                if refG not in genesIDs:
                    self.Genes[refG] = self.refseq.Genes[refG].mergeGenes(self.ensembl.Genes[ensG])
                    genesIDs.add(refG)
                self.Proteins[refP] = self.idConv.FillInMissingProteins(self.refseq.Proteins[refP])
                self.Domains[refP] = self.CompMergeDomainLists(self.refseq.Domains.get(refP, []),
                                                               self.ensembl.Domains.get(ensP, []))
                writtenIDs.add(ensT)
                writtenIDs.add(refT)
            else:  # else - separate the records
                # refseq records
                self.Transcripts[refT] = self.refseq.Transcripts[refT]
                refG = self.Transcripts[refT].gene_GeneID
                if refG not in genesIDs:
                    self.Genes[refG] = self.refseq.Genes[refG]
                    genesIDs.add(refG)
                self.Proteins[refP] = self.refseq.Proteins[refP]
                self.Domains[refP] = self.refseq.Domains.get(refP, [])
                writtenIDs.add(refT)
                if ensP in self.ensembl.Proteins:  # ensembl records
                    self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                    ensG = self.Transcripts[ensT].gene_ensembl
                    if ensG not in genesIDs:
                        self.Genes[ensG] = self.ensembl.Genes[ensG]
                        genesIDs.add(ensG)
                    self.Proteins[ensP] = self.ensembl.Proteins[ensP]
                    self.Domains[ensP] = self.ensembl.Domains.get(ensP, [])

                    self.mismatches_sep.append((ensP, refP,))
                    writtenIDs.add(ensT)

        for ensT, record in self.ensembl.Transcripts.items():
            if ensT not in writtenIDs:
                ensP = record.protein_ensembl
                if ensP is None or ensP not in self.ensembl.Proteins:
                    continue
                self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                self.Proteins[ensP] = self.ensembl.Proteins[ensP]
                ensG = record.gene_ensembl
                if ensG not in genesIDs:
                    self.Genes[ensG] = self.ensembl.Genes[ensG]
                    genesIDs.add(ensG)
                self.Domains[ensP] = self.ensembl.Domains.get(ensP, [])

    def CompMergeDomainLists(self, doms1, doms2):
        if len(doms1) == 0:
            return doms2
        elif len(doms2) == 0:
            return doms1
        finalList = list(doms1)
        for dom in doms1:
            for refDom in doms2:
                if dom != refDom:
                    finalList.append(refDom)
        return tuple(finalList)


if __name__ == '__main__':
    start_time = time.time()
    species = "M_musculus"
    col = Collector(species)
    col.collectAll()
    print("--- %s seconds ---" % (time.time() - start_time))
