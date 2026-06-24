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
from recordTypes import CanonicalEnum


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

    def _register_gene_id_mapping(self, ensembl_id, geneid_id, ensembl_to_geneid_map, verbose=False):
        """
        Register a mapping from gene_ensembl_id to gene_GeneID_id.
        Ensures one-to-one mapping to prevent duplicates.

        Returns: The canonical gene_GeneID_id to use for this ensembl_id.
        """
        if not ensembl_id:
            return geneid_id

        if ensembl_id in ensembl_to_geneid_map:
            existing_geneid = ensembl_to_geneid_map[ensembl_id]
            if existing_geneid != geneid_id and geneid_id is not None:
                # Conflict: same ensembl_id mapped to different geneid
                if verbose:
                    print(f"  WARNING: Ensembl ID {ensembl_id} already mapped to "
                          f"{existing_geneid}, but also found {geneid_id}. Keeping {existing_geneid}")
            return existing_geneid
        else:
            # Register new mapping
            ensembl_to_geneid_map[ensembl_id] = geneid_id
            return geneid_id

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
        #Combine the Transcrips, Gene, Protein, Domains data from refseq and ensembl
        print("Merging Transcript, Gene, Protein Data from Sources")
        # recombine = {}
        # ensembls = set()
        writtenIDs = set()
        genesIDs = set()
        
        # Once a gene_ensembl_id is assigned to a gene_GeneID_id, it must always use that pairing.
        ensembl_to_geneid_map = {}
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
        transcripts_mismaches = 0
        transcripts_matches = 0
        print(f'Starting going over refseq transcripts: {len(ref_transcripts)}')
        for refT, record in ref_transcripts.items():
            count += 1
            if count % 10000 == 0:
                print(f'\t #{count}')
            #if refT[1] == "R":  # only protein coding
            #    continue
            ensT = t_map.get(refT, None)
            if ensT and record.ensembl:
                if record.ensembl != ensT:
                    print(f"Transcript ID mismatch for {refT}: refseq has {record.ensembl} and idConv has {ensT}")
                    #raise ValueError(f"Transcript ID mismatch for {refT}: refseq has {record.ensembl} and idConv has {ensT}")
                    transcripts_mismaches += 1
                    ensT = record.ensembl
                else:
                    transcripts_matches += 1
                    
            elif ensT is None and record.ensembl:
                ensT = record.ensembl
                
            if record.protein_refseq is None or record.protein_refseq == '-':
                record.protein_refseq = self.refseq.trans2pro.get(refT, None)
            refP = record.protein_refseq
            ensP = p_map.get(refP, None)
            #if refP is None or refP not in ref_proteins:  # if no matching protein - ignore the transcript @@AM
            #    continue
            ensPflag = ensP in ens_proteins
            ensTflag = ensT in ens_transcripts
            if not ensTflag and ensPflag:
                tempensT = self.ensembl.pro2trans[ensP]
                if ensT is None:
                    record.ensembl = tempensT
                ensT = tempensT
            elif ensTflag and not ensPflag:
                ensP = self.ensembl.trans2pro.get(ensT, None)

            refG = record.gene_GeneID
            ensG = g_map.get(refG, None)

            ensG = self._register_gene_id_mapping(ensG, refG, ensembl_to_geneid_map, verbose=False)

            # Mark ensG as processed immediately after mapping, regardless of transcript outcome
            if ensG is not None:
                genesIDs.add(ensG)

            # This prevents genes without transcripts from being created.
            transcript_will_be_added = False

            if ensP and ensP in ens_proteins and abs(int(ref_proteins[refP].length) - int(ens_proteins[ensP].length)) <= 1:  # if the diff between protein length is smaller than 1- ignore
                self.mismatches_merged.append((ensP, refP,))
                self.Transcripts[refT] = fill_trans(record)
                transcript_will_be_added = True

                # This prevents the issue where both RefSeq and Ensembl exons end up in same transcript
                if ensT:
                    ens_record  = ens_transcripts.get(ensT, None)
                    if ens_record:
                        # Prefer Ensembl exons as they're generally more complete and accurate
                        if ens_record.exon_starts and len(ens_record.exon_starts) > 0:
                            self.Transcripts[refT].exon_starts = ens_record.exon_starts.copy()
                        if ens_record.exon_ends and len(ens_record.exon_ends) > 0:
                            self.Transcripts[refT].exon_ends = ens_record.exon_ends.copy()

                        if ens_record.canonical == CanonicalEnum.ENSEMBL:
                            if record.canonical == CanonicalEnum.REFSEQ:
                                self.Transcripts[refT].canonical = CanonicalEnum.BOTH
                            else:
                                self.Transcripts[refT].canonical = CanonicalEnum.ENSEMBL
                self.Proteins[refP] = fill_prot(ref_proteins[refP])
                self.Proteins[refP].mergeDescription(ens_proteins[ensP])
                self.Domains[refP] = merge_domains(self.refseq.Domains.get(refP, []),
                        self.ensembl.Domains.get(ensP, []))
                writtenIDs.add(ensT)
                writtenIDs.add(refT)
            else:  # separate the records
                # refseq records
                self.Transcripts[refT] = ref_transcripts[refT]
                self.Transcripts[refT].gene_ensembl = ensG
                self.Proteins[refP] = ref_proteins[refP]
                self.Domains[refP] = self.refseq.Domains.get(refP, [])
                writtenIDs.add(refT)
                transcript_will_be_added = True
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
                        refG = ensembl_to_geneid_map.get(ensG, g_map.get(ensG, None))
                    else:
                        # Use registered mapping to ensure consistency
                        refG = ensembl_to_geneid_map.get(ensG, refG)

                    # Register this mapping to prevent future conflicts
                    refG = self._register_gene_id_mapping(ensG, refG, ensembl_to_geneid_map, verbose=True)

                    self.Transcripts[ensT].gene_GeneID = refG
                    self.Proteins[ensP] = ens_proteins[ensP]
                    self.Domains[ensP] = self.ensembl.Domains.get(ensP, [])
                    self.mismatches_sep.append((ensP, refP,))
                    writtenIDs.add(ensT)
                    transcript_will_be_added = True
                    # Gene will be added after this block
                elif ensT not in ens_transcripts:
                    self.Transcripts[refT] = fill_trans(record)
                    self.Proteins[refP] = fill_prot(ref_proteins[refP])
                    transcript_will_be_added = True

            # Add gene ONLY if transcript was successfully added
            if transcript_will_be_added:
                if refG not in self.Genes:
                    self.Genes[refG] = self.refseq.Genes[refG].mergeGenes(self.ensembl.Genes.get(ensG, ensG))
                    genesIDs.add(refG)
                    # ensG already added to genesIDs right after _register_gene_id_mapping()
        print(f'Total refseq transcripts {count} mismatches: {transcripts_mismaches}, matches: {transcripts_matches}')
        # ~~~~ End of RefSeq Loop ~~~~~

        count = 0
        print(f'Starting going over ensembl transcripts: {len(ens_transcripts)}')
        for ensT, record in ens_transcripts.items():
            count += 1
            if count % 1000 == 0:
                print(f'\t #{count}')
            if ensT not in writtenIDs:
                self.Transcripts[ensT] = fill_trans(record)
                ensP = record.protein_ensembl
                refT = t_map.get(ensT, None)
                #if ensP is None or ensP not in ens_proteins or (refT is not None and refT[1] == "R"): @@AM
                #if (refT is not None and refT[1] == "R"):
                #    continue
                if refT:
                    ref_record  = ref_transcripts.get(refT, None)
                    if ref_record:
                        if ref_record.canonical == CanonicalEnum.REFSEQ:
                            if self.Transcripts[ensT].canonical == CanonicalEnum.ENSEMBL:
                                self.Transcripts[ensT].canonical = CanonicalEnum.BOTH
                            else:   
                                 self.Transcripts[ensT].canonical = CanonicalEnum.REFSEQ
                        self.Transcripts[ensT].canonical = ref_record.canonical
                # self.Transcripts[ensT] = self.ensembl.Transcripts[ensT]
                # self.Proteins[ensP] = self.ensembl.Proteins[ensP]
                refP = record.protein_refseq
                
                if ensP:
                    self.Proteins[ensP] = fill_prot(ens_proteins[ensP])
                    if refP:
                        self.Proteins[ensP].mergeDescription(ref_proteins.get(refP, None))
                    self.Domains[ensP] = merge_domains(self.refseq.Domains.get(refP, []),
                                                                    self.ensembl.Domains.get(ensP, []))
                
                ensG = self.Transcripts[ensT].gene_ensembl
                refG = self.Transcripts[ensT].gene_GeneID

                # NOTE: Safe to add genes here because transcript was already added 
                # Ensure consistent mapping for ensembl gene IDs
                if ensG in ensembl_to_geneid_map:
                    canonical_refG = ensembl_to_geneid_map[ensG]
                    if refG != canonical_refG and refG is not None:
                        print(f"  CONFLICT: Ensembl {ensG} mapped to {refG} but already registered as {canonical_refG}. Using {canonical_refG}")
                    refG = canonical_refG
                    self.Transcripts[ensT].gene_GeneID = refG
                else:
                    # Register new mapping
                    if refG:
                        ensembl_to_geneid_map[ensG] = refG
                    elif refG is None and ensG:
                        # No RefSeq mapping - use ensG as key
                        ensembl_to_geneid_map[ensG] = None

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
