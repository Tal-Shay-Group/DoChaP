class Gene:

    def __init__(self, GeneID, ensembl, symbol, synonyms, chromosome, strand, transcripts):
        self.GeneID = GeneID
        self.ensembl = ensembl
        self.symbol = symbol
        self.synonyms = synonyms
        self.chromosome = chromosome
        self.strand = strand
        self.transcripts = transcripts


class Transcript:

    def __init__(self, refseq, ensembl, chrom, strand, tx, CDS, gene, prot_ref, exons_starts, exons_ends):
        self.refseq = refseq
        self.ensembl = ensembl
        self.chrom = chrom
        self.strand = strand
        self.tx = tx
        self.CDS = CDS
        self.gene = gene
        self.prot_ref = prot_ref
        if len(exons_starts) == len(exons_ends):
            self.exon_starts = exons_starts
            self.exon_ends = exons_ends
        else:
            raise ValueError('different number of Exons starts and Exons ends')

    def countExons(self):
        return len(self.exon_starts)

    def exons2abs(self):
        if len(self.exon_starts) != len(self.exon_ends):
            raise ValueError('Arguments 1 and 2: Expected same length for the lists/tuples of start and stop positions')
        elif len(self.CDS) != 2:
            raise ValueError('3rd argument: Expected list of 2 values: CDS_start, CDS_end')
        elif self.strand != '-' and self.strand != '+':
            raise ValueError('4th argument: Expected strand: + or -, for forward and reverse (respectively)')
        transcript_len = 0
        abs_start = []
        abs_stop = []
        add_opt = 0
        if self.strand == '-':
            stop_list = self.exon_ends.copy()[::-1]
            start_list = self.exon_starts.copy()[::-1]
            add_opt = 1
        else:
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

    def __repr__(self):
        print(self.refseq + ' / ' + self.ensembl)

    def compare_transcript(self, other):
        if self.refseq is not None and other.refseq is not None:
            return self.refseq == other.refseq
        elif self.ensembl is not None and other.ensembl is not None:
            return self.ensembl == other.ensembl
        else:
            return self.strand == other.strand and \
                   self.exon_starts == other.exon_starts and \
                   self.exon_ends == other.exon_ends


