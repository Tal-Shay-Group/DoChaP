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
        t_map = self.idConv.transcriptCon
        g_map = self.idConv.geneCon
        p_map = self.idConv.proteinCon
        ref_transcripts = self.refseq.Transcripts
        ref_proteins = self.refseq.Proteins
        ens_transcripts = self.ensembl.Transcripts
        ens_proteins = self.ensembl.Proteins
        # use local function instead of redicrect
        merge_domains = self.CompMergeDomainLists
        fill_trans = self.idConv.FillInMissingsTranscript
        fill_prot = self.idConv.FillInMissingProteins
        count = 0
        print(f'Starting going over refseq transcripts: {len(ref_transcripts)}')
        for refT, record in ref_transcripts.items():
            count += 1
            if count % 1000 == 0:
                print(f'\t #{count}')
            if refT[1] == "R":  # only protein coding
                continue
            ensT = t_map.get(refT, None)
            if record.protein_refseq is None or record.protein_refseq == '-':
                record.protein_refseq = self.refseq.trans2pro.get(refT, None)
            refP = record.protein_refseq
            ensP = p_map.get(refP, None)
            if refP is None or refP not in ref_proteins:  # if no matching protein - ignore the transcript
                continue
            ensPflag = ensP in ens_proteins
            ensTflag = ensT in ens_transcripts
            if not ensTflag and ensPflag:
                tempensT = self.ensembl.pro2trans[ensP]
                if ensT is None:
                    record.ensembl = tempensT
                ensT = tempensT
            elif ensTflag and not ensPflag:
                ensP = self.ensembl.trans2pro[ensT]

            refG = record.gene_GeneID
            ensG = g_map.get(refG, None)

            # add gene to dict
            if refG not in self.Genes:
                self.Genes[refG] = self.refseq.Genes[refG].mergeGenes(self.ensembl.Genes.get(ensG, ensG))
                genesIDs.add(refG)
                if ensG is not None:
                    genesIDs.add(ensG)

            if ensP in ens_proteins and abs(int(ref_proteins[refP].length) - int(ens_proteins[ensP].length)) <= 1:  # if the diff between protein length is smaller than 1- ignore
                self.mismatches_merged.append((ensP, refP,))
                self.Transcripts[refT] = fill_trans(record)
                self.Proteins[refP] = fill_prot(ref_proteins[refP])
                self.Proteins[refP].mergeDescription(ens_proteins[ensP])
                self.Domains[refP] = merge_domains(self.refseq.Domains.get(refP, []),
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
                self.Transcripts[refT] = ref_transcripts[refT]
                self.Transcripts[refT].gene_ensembl = ensG
                self.Proteins[refP] = ref_proteins[refP]
                self.Domains[refP] = self.refseq.Domains.get(refP, [])
                writtenIDs.add(refT)
                # if refG not in self.Genes:
                #     self.Genes[refG] = self.refseq.Genes[refG].mergeGenes(self.ensembl.Genes.get(ensG, ensG))
                #     genesIDs.add(refG)
                #     if ensG is not None:
                #         genesIDs.add(ensG)
                # ensembl records
                if ensP in ens_proteins:
                    self.Transcripts[ensT] = ens_transcripts[ensT]
                    if ensG != self.Transcripts[ensT].gene_ensembl:
                        ensG = self.Transcripts[ensT].gene_ensembl
                        refG = g_map.get(ensG, None)
                    self.Transcripts[ensT].gene_GeneID = refG
                    self.Proteins[ensP] = ens_proteins[ensP]
                    self.Domains[ensP] = self.ensembl.Domains.get(ensP, [])
                    self.mismatches_sep.append((ensP, refP,))
                    writtenIDs.add(ensT)
                    if refG is None:
                        self.Genes[ensG] = self.ensembl.Genes[ensG]
                        genesIDs.add(ensG)
                    elif refG not in self.Genes:
                        self.Genes[refG] = self.ensembl.Genes[ensG].mergeGenes(self.refseq.Genes.get(refG, refG))
                        genesIDs.add(refG)
                        if ensG is not None:
                            genesIDs.add(ensG)
                elif ensT not in ens_transcripts:
                    self.Transcripts[refT] = fill_trans(record)
                    self.Proteins[refP] = fill_prot(ref_proteins[refP])
        # ~~~~ End of RefSeq Loop ~~~~~

        count = 0
        print(f'Starting going over ensembl transcripts: {len(ens_transcripts)}')
        for ensT, record in ens_transcripts.items():
            count += 1
            if count % 1000 == 0:
                print(f'\t #{count}')
            if ensT not in writtenIDs:
                ensP = record.protein_ensembl
                refT = t_map.get(ensT, None)
                if ensP is None or ensP not in ens_proteins or (refT is not None and refT[1] == "R"):
                    continue
                self.Transcripts[ensT] = fill_trans(record)
                # self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                # self.Proteins[ensP] = self.ensembl.Proteins[ensP]
                refP = record.protein_refseq
                self.Proteins[ensP] = fill_prot(ens_proteins[ensP])
                self.Proteins[ensP].mergeDescription(ref_proteins.get(refP, None))
                self.Domains[ensP] = merge_domains(self.refseq.Domains.get(refP, []),
                                                               self.ensembl.Domains.get(ensP, []))
                ensG = self.Transcripts[ensT].gene_ensembl
                refG = self.Transcripts[ensT].gene_GeneID
                if refG in self.Genes:
                    if ensG == g_map.get(refG, None) or g_map.get(refG, None) is None:
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
