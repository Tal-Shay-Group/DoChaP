import re
import copy

class Gene:

    def __init__(self, GeneID=None, ensembl=None, symbol=None, synonyms=None, chromosome=None, strand=None):
        self.GeneID = GeneID
        self.ensembl = ensembl
        self.symbol = symbol
        self.synonyms = synonyms
        self.chromosome = chromosome
        self.strand = strand

    # def __repr__(self):
    #    print('GeneID: ' + self.GeneID + ' / ' + self.ensembl)

    def compareGenes(self, other):
        if self.GeneID == other.GeneID and self.ensembl == other.ensembl:
            return True
        elif (self.GeneID is None or other.GeneID is None) and self.ensembl == other.ensembl:
            return True
        elif (self.ensembl is None or other.ensembl is None) and self.GeneID == other.GeneID:
            return True
        else:
            return False

    def mergeGenes(self, other):
        attr = ['GeneID', 'ensembl', 'symbol', 'synonyms', 'chromosome', 'strand']
        for at in attr:
            if self.__getattribute__(at) is None:
                self.__setattr__(at, other.__getattribute__(at))
        syno = other.synonyms.split("; ") + [other.symbol] if other.synonyms is not None else [other.symbol]
        for name in syno:
            if self.synonyms is not None and name not in self.synonyms.split("; ") + [self.symbol]:
                self.synonyms = self.synonyms + "; " + name
            elif self.synonyms is None and self.symbol != other.symbol:
                self.synonyms = other.symbol
        return self


class Transcript:

    def __init__(self, refseq=None, ensembl=None, chrom=None, strand=None, tx=None, CDS=None,
                 GeneID=None, gene_ensembl=None, geneSymb=None, protein_refseq=None, protein_ensembl=None,
                 exons_starts=[],
                 exons_ends=[]):
        self.refseq = refseq
        self.ensembl = ensembl
        self.chrom = chrom
        self.strand = strand
        self.tx = tx
        self.CDS = CDS
        self.gene_GeneID = GeneID
        self.gene_ensembl = gene_ensembl
        self.geneSymb = geneSymb
        self.protein_refseq = protein_refseq
        self.protein_ensembl = protein_ensembl
        if len(exons_starts) == len(exons_ends):
            self.exon_starts = exons_starts
            self.exon_ends = exons_ends
        else:
            raise ValueError('different number of Exons starts and Exons ends')

    def setEnsemble(self, ensembl):
        self.ensembl = ensembl

    def countExons(self):
        return len(self.exon_starts)

    def __repr__(self):
        rep = (self.refseq, self.ensembl)
        return str(rep)

    def idNoVersion(self, idType='refseq'):
        tid = self.__getattribute__(idType)
        if tid is not None:
            return tid.split(".")[0]
        else:
            return None

    def idVersion(self, idType='refseq'):
        tid = self.__getattribute__(idType)
        if tid is not None:
            if tid.startswith("mito"):
                return "mito"
            else:
                return tid.split(".")[1]
        else:
            return None

    def exons2abs(self):
        if len(self.exon_starts) != len(self.exon_ends):
            raise ValueError('Expected same length for the lists/tuples of start and stop positions')
        elif len(self.CDS) != 2:
            raise ValueError('Expected list of 2 values: CDS_start, CDS_end')
        elif self.strand != '-' and self.strand != '+':
            raise ValueError('Expected strand: + or -, for forward and reverse (respectively)')
        transcript_len = 0
        abs_start = []
        abs_stop = []
        add_opt = 0
        # if self.strand == '-':
        #     stop_list = self.exon_ends.copy()[::-1] #if self.exon_starts[0] > self.exon_starts[-1] else self.exon_ends.copy()
        #     start_list = self.exon_starts.copy()[::-1] #if self.exon_starts[0] > self.exon_starts[-1] else self.exon_starts.copy()
        #     add_opt = 1
        # else:
        stop_list = self.exon_ends.copy()
        start_list = self.exon_starts.copy()
        for i in range(len(start_list)):
            if stop_list[i] < self.CDS[0]:
                abs_start.append(0)
                abs_stop.append(0)
                continue
            elif start_list[i] < self.CDS[0] < stop_list[i]:
                start_list[i] = self.CDS[0]
            if start_list[i] > self.CDS[1]:
                abs_start.append(0)
                abs_stop.append(0)
                continue
            elif stop_list[i] > self.CDS[1] > start_list[i]:
                stop_list[i] = self.CDS[1] + add_opt
            abs_start.append(transcript_len + 1)
            curr_length = stop_list[i] - start_list[i]
            abs_stop.append(transcript_len + curr_length)
            transcript_len = transcript_len + curr_length
        return abs_start, abs_stop

    def compare_transcript(self, other):
        if self.refseq is not None and other.refseq is not None:
            return self.refseq == other.refseq
        elif self.ensembl is not None and other.ensembl is not None:
            return self.ensembl == other.ensembl
        else:
            return self.strand == other.strand and \
                   self.exon_starts == other.exon_starts and \
                   self.exon_ends == other.exon_ends

    def mergeTranscripts(self, other):
        attr = ['refseq', 'ensembl', 'chrom', 'strand', 'tx', 'CDS', 'gene_GeneID', 'gene_ensembl',
                'geneSymb', 'protein_refseq', 'protein_ensembl', 'exon_starts', 'exon_ends']
        if (self.idVersion() is not None and other.idVersion() is not None) and \
                (self.idVersion("ensembl") is not None and other.idVersion("ensembl") is not None):
            if self.idVersion() > other.idVersion() or self.idVersion("ensembl") > other.idVersion("ensembl"):
                return self
            elif self.idVersion() < other.idVersion() or self.idVersion("ensembl") < other.idVersion("ensembl"):
                return other
            else:
                mergedT = copy.deepcopy(self)
        for atribute in attr:
            if mergedT.__getattribute__(atribute) is None:
                mergedT.__setattr__(atribute, other.__getattribute__(atribute))
        return mergedT


class Domain:

    def __init__(self, ext_id, start=None, end=None, cddId=None, name=None, note=None):
        self.suppTypes = {'cd': 'cd', 'cl': 'cl', 'pfam': 'pfam', 'pf': 'pfam',
                          'smart': 'smart', 'sm': 'smart', 'tigr': 'tigr', 'ipr': 'interpro'}
        self.aaStart = start
        self.aaEnd = end
        if self.aaStart is not None:
            self.nucStart = (self.aaStart * 3) - 2  # start position, including
        if self.aaEnd is not None:
            self.nucEnd = self.aaEnd * 3  # end position, including!!!
        self.name = name
        self.note = note
        self.cdd = cddId
        if ext_id is not None:
            prefix = re.sub(r"\d+$", "", ext_id.lower())
            if prefix in self.suppTypes.keys():
                self.extType = self.suppTypes[prefix]
                self.extID = ext_id.lower().replace(prefix, self.suppTypes[prefix])
            else:
                raise ValueError('Unknown external ID prefix: ' + ext_id)
        elif ext_id is None and self.cdd is None:
            raise ValueError('Domain obj not supporting NoneType external ID')
        else:
            self.extID = None

    def domain_exon_relationship(self, exon_starts, exon_ends):
        domain_nuc_positions = (self.nucStart, self.nucEnd,)
        for ii in range(len(exon_starts)):
            if exon_starts[ii] <= domain_nuc_positions[0] <= exon_ends[ii]:
                if domain_nuc_positions[1] <= exon_ends[ii]:
                    return 'complete_exon', ii + 1, domain_nuc_positions[1] - domain_nuc_positions[0] + 1
                else:
                    flag = 0
                    jj = ii + 1
                    length = [-1 * (exon_ends[ii] - domain_nuc_positions[0] + 1)]
                    while flag == 0 and jj < len(exon_starts):
                        if exon_starts[jj] <= domain_nuc_positions[1] <= exon_ends[jj]:
                            flag = 1
                            length.append(domain_nuc_positions[1] - exon_starts[jj] + 1)
                        else:
                            length.append(exon_ends[jj] - exon_starts[jj] + 1)
                        jj += 1
                    return 'splice_junction', list(range(ii + 1, jj + 1)), length
        return None, None, None

    def __eq__(self, other):
        if self.extID == other.extID and self.aaStart == other.aaStart and self.aaEnd == other.aaEnd:
            return True
        else:
            return False

class Protein:
    def __init__(self, refseq=None, ensembl=None, descr=None, length=None, synonyms=None, transcript_refseq=None, transcript_ensembl=None):
        self.refseq = refseq
        self.ensembl = ensembl
        self.description = descr
        self.length = length
        self.synonyms = synonyms
        self.transcript_refseq = transcript_refseq
        self.transcript_ensembl = transcript_ensembl

    def refseqNoVersion(self):
        return self.refseq.split('.')[0]
