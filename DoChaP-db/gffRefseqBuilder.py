# import ftplib
# import gzip
import os
import sys
# import datetime
import gffutils
from Bio import SeqIO
import re

sys.path.append(os.getcwd())
from recordTypes import *
from Director import SourceBuilder
from ftpDownload import ftpDownload
from conf import *


class RefseqBuilder(SourceBuilder):
    """
    Download and parse RefSeq data: genomic data from genomic.gff protein domains from Genebank flatfilesa
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        # self.SpeciesConvertor = {'M_musculus': 'Mus_musculus', 'H_sapiens': 'Homo_sapiens',
        #                          'R_norvegicus': 'Rattus_norvegicus',
        #                          'D_rerio': 'Danio_rerio', 'X_tropicalis': 'Xenopus_tropicalis'}
        self.species = species
        # self.speciesTaxonomy = {"Mus_musculus": "vertebrate_mammalian", "Homo_sapiens": "vertebrate_mammalian",
        #                         'Danio_rerio': "vertebrate_other", "Xenopus_tropicalis": "vertebrate_other",
        #                         "Rattus_norvegicus": "vertebrate_mammalian"}
        self.savePath = os.getcwd() + '/data/{}/refseq/'.format(self.species)
        os.makedirs(self.savePath, exist_ok=True)
        self.gff = self.FilesNoDownload("gff")
        # self.gpff = self.savePath + "protein.gpff"
        self.gpff = self.FilesNoDownload("gpff")
        self.Transcripts = {}
        self.Domains = {}
        self.ignoredDomains = {}
        self.regionChr = {}
        self.Proteins = {}
        self.Genes = {}
        self.pro2trans = {}
        self.trans2pro = {}

    def downloader(self):
        """ This method is downloading the required data files directly from ftp site"""
        skey = SpeciesConvertor[self.species]
        ftp_address = 'ftp.ncbi.nlm.nih.gov'
        # if skey in ["Rattus_norvegicus", "Xenopus_tropicalis"]:
        #     ftp_path = '/genomes/refseq/{}/{}/representative/'.format(speciesTaxonomy[skey], skey)
        # else:
        #     ftp_path = '/genomes/refseq/{}/{}/latest_assembly_versions/'.format(speciesTaxonomy[skey], skey)

        # Downloading gff files (genomic data):
        ftp_path = '/genomes/refseq/{}/{}/{}/'.format(speciesTaxonomy[skey], skey, ftpDirPath[skey])

        def FindFile(listOfFiles):
            for file in listOfFiles:
                if len(listOfFiles) > 1:
                    raise ValueError("More than 1 file in dir")
                else:
                    genomeVersion = listOfFiles[0]
                gff = [genomeVersion + "/" + genomeVersion + "_genomic.gff", "genomic.gff"]
                return [gff]

        down = ftpDownload(species=skey, ftp_adress=ftp_address, ftp_path=ftp_path, savePath=self.savePath,
                           specifyPathFunc=FindFile)
        filesDownloaded = down.Download()
        self.gff = filesDownloaded[0]

        # Downloading gpff files (protein data):
        ftp_path = '/refseq/{}/mRNA_Prot/'.format(self.species)

        def FindFile(listOfFiles):
            return [[f[:-3], f[:-3]] for f in listOfFiles if "protein.gpff.gz" in f]

        down = ftpDownload(species=skey, ftp_adress=ftp_address, ftp_path=ftp_path, savePath=self.savePath,
                           specifyPathFunc=FindFile)
        self.gpff = down.Download()

    def FilesNoDownload(self, suffix):
        """ When running RefseqBuilder without re-downloading the data,
        this method finds all the files (with the relevant suffix) saved in the specified directory"""

        le = len(suffix)
        files = [self.savePath + "/" + file for file in os.listdir(self.savePath) if file[-le:] == suffix]
        if suffix == "gff" and len(files) != 0:
            files = files[0]
        return files

    def parser(self):
        """ This method is the main parser of RefSeq data (both genomic and proteins)
        which is called by the director"""

        print("-------- Refseq data Parsing --------")
        self.ParseGffRefseq()
        for gpff_file in self.gpff:
            self.parseSingleGpff(gpff_file)
        GffnoGpff = set(self.Transcripts.keys()).difference(set(self.trans2pro.keys()))
        print("\t{} transcripts from gff file were not found in the gpff file".format(len(GffnoGpff)))
        for k in GffnoGpff:
            del self.Transcripts[k]

    def ParseGffRefseq(self):
        """ This method is the parser of gff genomic data of RefSeq
        Attention to the OPTIONS (1-3) choose OPT1 / OPT2+OPT3 / OPT3"""

        print("\tParsing gff3 file...")

        # # # OPT1 - Use when running from cluster
        # print("\tcreating temporary database from file: " + self.gff)
        # fn = gffutils.example_filename(self.gff)
        # db = gffutils.create_db(fn, ":memory:", merge_strategy="create_unique")
        # #
        # # # OPT2 - Use when running localy and need to create a local temporary database, must be used with OPT3
        # gffutils.create_db(fn, "DB.Refseq_" + self.species[0] +".db", merge_strategy="create_unique")
        # #
        # # # OPT3 - Use when using OPT2 or when running locally and the temp db is already created
        db = gffutils.FeatureDB("DB.Refseq_" + self.species[0] +".db")
        # #
        self.collectChromosomeRegions(db)
        self.collect_genes(db)
        curretGenes = self.Genes.copy()
        self.Genes = {}
        print("\tCollecting Transcripts data from gff file...")
        self.Transcripts = {}
        transcript2region = {}

        for t in db.features_of_type("mRNA"):
            newT = Transcript()
            if self.regionChr[t.chrom] == "ALT_chr" or self.regionChr[t.chrom] == "Unknown":  # ignore alternative chromosomes
                continue
            elif "inference" in t.attributes and t["inference"][0].startswith("similar to RNA"):  # ignore pseudogenes
                continue
            elif len(t["ID"][0].split("-")) > 2:  # remove duplicated records (PAR in X and Y chr will be taken only from X)
                continue
            newT.chrom = self.regionChr[t.chrom]
            newT.tx = (t.start - 1, t.end,)  # gff format is 1 based start, change to 0-based-start
            newT.strand = t.strand
            newT.refseq = t["transcript_id"][0]
            newT.gene_GeneID = [info for info in t["Dbxref"] if info.startswith("GeneID")][0].split(":")[1]
            newT.geneSymb = t["gene"][0]
            self.Transcripts[newT.refseq] = newT
            self.Genes[newT.gene_GeneID] = curretGenes[newT.gene_GeneID]
            transcript2region[newT.refseq] = t.chrom

        print("\tCollecting CDS data from gff file...")
        for cds in db.features_of_type("CDS"):
            if self.regionChr[cds.chrom] == "ALT_chr" or self.regionChr[cds.chrom] == "Unknown":
                continue
            elif self.regionChr[cds.chrom] == "MT":
                GeneID = [info for info in cds["Dbxref"] if info.startswith("GeneID")][0].split(":")[1]
                ref = "mito-" + GeneID
                self.Transcripts[ref] = Transcript(refseq=ref, chrom=self.regionChr[cds.chrom], strand=cds.strand,
                                                   tx=(cds.start, cds.end), CDS=(cds.start, cds.end),
                                                   GeneID=GeneID, geneSymb=cds["gene"][0],
                                                   protein_refseq=cds["Name"][0], exons_starts=[cds.start],
                                                   exons_ends=[cds.end])
                self.Genes[GeneID] = curretGenes[GeneID]
            else:
                ref = [info if info.startswith("rna-") else '-0' for info in cds["Parent"]][0].split("-")
                if ref[1][0] == '0' or transcript2region.get(ref[1], '') != cds.chrom or len(ref) > 2:
                    # ignore long non-coding rna
                    # ignore rearrangement records (immunoglobulin compartments, alternative chrom)
                    # ignore non duplicated records (PAR in X and Y chr will be taken only from X)
                    continue
                ref = ref[1]
                if ref not in self.Transcripts.keys():
                    continue
                self.Transcripts[ref].protein_refseq = cds["Name"][0]
                current_CDS = self.Transcripts[ref].CDS
                if current_CDS is not None:
                    cds_start = cds.start - 1 if cds.start < current_CDS[0] else current_CDS[0]
                    cds_end = cds.end if cds.end > current_CDS[1] else current_CDS[1]
                else:
                    cds_start = cds.start - 1  # gff format is 1 based start, this entire code is for 0 based start
                    cds_end = cds.end
                self.Transcripts[ref].CDS = (cds_start, cds_end,)

        print("\tCollecting Exons data from gff file...")
        for e in db.features_of_type("exon"):
            ref = e["ID"][0].split("-")
            if self.regionChr[e.chrom] == "ALT_chr" or e["gbkey"][0] != "mRNA" \
                    or transcript2region.get(ref[1], '') != e.chrom or len(ref) > 3:
                continue  # ignore alternative chromosome and exons of duplicated genes
            ref = ref[1]
            if ref not in self.Transcripts.keys():
                continue
            orderInT = int(e["ID"][0].split("-")[2])
            l_orig = len(self.Transcripts[ref].exon_starts)
            self.Transcripts[ref].exon_starts = self.Transcripts[ref].exon_starts + [None] * (orderInT - l_orig)
            self.Transcripts[ref].exon_ends = self.Transcripts[ref].exon_ends + [None] * (orderInT - l_orig)
            self.Transcripts[ref].exon_starts[orderInT - 1] = e.start - 1
            self.Transcripts[ref].exon_ends[orderInT - 1] = e.end

    def collect_genes(self, db):
        """ This method collects all the genes from gff file """
        print("\tCollecting genes data from gff3 file...")
        for g in db.features_of_type("gene"):
            geneID = g["Dbxref"][0].split(":")[1]
            syno = g["gene_synonym"] if "gene_synonym" in g.attributes else " "
            syno = syno[0].replace(",", "; ")
            newG = Gene(GeneID=geneID, symbol=g["gene"][0], chromosome=self.regionChr[g.chrom], strand=g.strand,
                        synonyms=syno)
            if newG.GeneID in self.Genes.keys() and newG.chromosome != "ALT_chr" and newG.chromosome != "Unknown":
                #  Genes of pseudoautosomal region (X and Y) will be only taken from X (same coordinates)
                if newG.chromosome == "X" and self.Genes[newG.GeneID].chromosome == "Y":
                    self.Genes[newG.GeneID] = newG
                elif newG.chromosome == "Y" and self.Genes[newG.GeneID].chromosome == "X":
                    continue
                else:
                    raise ValueError(
                        "GeneID {}, chrom {} already in dict with chrom:{}".format(newG.GeneID,
                                                                                   newG.chromosome,
                                                                                   self.Genes[newG.GeneID].chromosome))
            elif newG.chromosome != "ALT_chr" and newG.chromosome != "Unknown":
                self.Genes[newG.GeneID] = newG

    def collectChromosomeRegions(self, db):
        """ This method translate the ID of the sequence region to the relevant chromosome"""
        self.regionChr = {}
        for r in db.features_of_type("region"):
            if "Name" in r.attributes:
                self.regionChr[r.chrom] = r["Name"][0]
        for feat in db.features_of_type("sequence_feature"):
            if feat.attributes.get("Note", " ")[0].startswith(
                    "Anchor sequence. This sequence is derived from alt loci"):
                self.regionChr[feat.chrom] = "ALT_chr"

    def parseSingleGpff(self, gpff_file):
        """ This method is parsing a single gpff file, calling other methods to organize proteins and domains data"""
        print("\tCollecting Proteins and Domains data from gpff file...")
        for rec in SeqIO.parse(gpff_file, 'gb'):
            if rec.name[0:2] == 'NP' or rec.name[0:2] == 'XP':  # takes both proteins and predictions!
                flag = self.protein_info(record=rec)
                self.regions_from_record(rec, flag)

    def regions_from_record(self, record, TranscriptFlag=True):
        """
        Organize "Region"s data from protein record parsed by SeqIO.parse from gpff file, to objects of class Domain.
        * start position in the protein + 1 (SeqIO shows 0-based start), DoChaP shows domains as 1-based-start
        * end position in the protein is already 1-based
        * Only region with external id are included, external id can start with pfam/smart/cl/cd etc.
        The function updates the Domains attr directly with tuple of Domain ogjects for each protein id.
        """
        if not TranscriptFlag:
            return
        regions = [feature for feature in record.features if feature.type == 'Region']
        parsed = []
        for reg in regions:
            start = reg.location.start.position + 1  # convert domains to be 1-based-start
            end = reg.location.end.position
            if len(reg.qualifiers) > 1 and 'region_name' in reg.qualifiers and start != end:  # only looking at regions larger than 1
                name = reg.qualifiers['region_name'][0]
                if 'note' in reg.qualifiers:
                    note = reg.qualifiers['note'][0]
                else:
                    note = None
                if re.match(r"PRK\d+", name):
                    ext_id = name
                elif note is not None:
                    if 'propagated from UniProtKB' in note:
                        note = note
                        ext_id = None
                    elif ';' in note:
                        noteSplit = note.split('; ')
                        ext_id = noteSplit[-1]
                        note = "; ".join(noteSplit[:-1])
                    else:
                        ext_id = None
                else:
                    ext_id = None
                if 'db_xref' not in reg.qualifiers:
                    if ext_id is None:
                        continue  # only records with external id
                    cdId = None
                else:
                    xref = reg.qualifiers.get('db_xref', [])
                    cdId = [i.split(':')[-1] for i in xref if i.startswith('CDD')][0]
                try:
                    newDomain = Domain(ext_id=ext_id, start=start, end=end, cddId=cdId, name=name, note=note)
                    parsed.append(newDomain)
                except ValueError:
                    self.ignoredDomains.update({'extId': ext_id, 'CDD': cdId})
        self.Domains[record.id] = tuple(parsed)

    def protein_info(self, record, TranscriptsDependent=True):
        """ Organize data from protein record parsed by SeqIO.parse from gpff file, to object of class Protein.
        Update Proteins attr directly.
        @return True when finish, False if no matched transcript in Transcript attr and not adding this record
        """
        withversion = record.id  # with version
        # refseq_id = record.name  # without version
        descr = record.description
        pro = [p for p in record.features if p.type == 'Protein'][0]
        length = pro.location.end.position  # length!!!
        try:
            note = pro.qualifiers['note'][0]
        except Exception:
            note = None
        cds = [c for c in record.features if c.type == 'CDS'][0]
        transcript = cds.qualifiers['coded_by'][0].split(':')[0]
        if TranscriptsDependent and transcript not in self.Transcripts:
            return False
        if transcript.startswith("join("):
            transcript.strip("join(")
        # xref = cds.qualifiers.get('db_xref', [])
        protein = Protein(refseq=withversion, ensembl=None, descr=descr, length=length, synonyms=note,
                          transcript_refseq=transcript)
        self.Proteins[protein.refseq] = protein
        self.pro2trans[protein.refseq] = transcript
        self.trans2pro[transcript] = protein.refseq
        return True


if __name__ == '__main__':
    rr = RefseqBuilder("H_sapiens")
    rr.parser()

