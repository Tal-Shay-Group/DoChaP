import ftplib
import gzip
import os
from OOP_project.Director import SourceBuilder
from OOP_project.recordTypes import Transcript


class UcscBuilder(SourceBuilder):
    """
    Download and parse UCSC tables
    """

    def __init__(self, species):
        SourceBuilder.__init__(self, species)
        ucsc_conversion = {'M_musculus': 'mm10', 'H_sapiens': 'hg38', 'R_norvegicus': 'rn6', 'D_rerio': 'danRer11',
                           'X_tropicalis': 'xenTro9'}
        self.ucscSpecies = ucsc_conversion[self.species]
        self.refseq = dict()
        self.ensembl = dict()
        self.downloadedT = tuple()
        self.combined = dict()

    def downloader(self):
        specie = self.species
        username = 'anonymous'
        pswd = 'example@post.bgu.ac.il'
        skey = self.ucscSpecies

        ftp_address = 'hgdownload.soe.ucsc.edu'
        print('connecting to: ' + ftp_address + '...')
        ftp = ftplib.FTP(ftp_address)
        print('logging in...')
        ftp.login(user=username, passwd=pswd)
        ftp_path = '/goldenPath/{}/database/'
        ftp.cwd(ftp_path.format(skey))
        download_path = os.getcwd() + '/data/{}/from_ucsc/'
        print('downloading files to : ' + download_path.format(self.species))
        os.makedirs(os.path.dirname(download_path.format(self.species)), exist_ok=True)
        tables = ['kgXref', 'knownGene', 'ncbiRefSeq', 'ensGene', 'ensemblToGeneName']  # 'refGene',
        allTables = ftp.nlst()
        for table in tables:
            if table + '.txt.gz' not in allTables:
                print('Table ' + table + ' not exist for species: ' + specie)
                continue
            table_path = download_path.format(self.species) + table + '.txt'
            print('downloading: ' + table + '.txt.gz..')
            ftp.sendcmd("TYPE i")
            with open(table_path + '.gz', 'wb') as f:
                def callback(chunk):
                    f.write(chunk)

                ftp.retrbinary("RETR " + table + '.txt.gz', callback)
            print('extracting...')
            inp = gzip.GzipFile(table_path + '.gz', 'rb')
            s = inp.read()
            inp.close()
            with open(table_path, 'wb') as f_out:
                f_out.write(s)
            print('removing compressed file...')
            os.remove(table_path + '.gz')
            self.downloadedT = tuple(list(self.downloadedT) + [table])

    def parse_ncbiRefSeq(self, table_path=os.getcwd() + '/data/{}/from_ucsc/ncbiRefSeq.txt'):
        """
        Parse the ncbiRefSeq table with the columns:
            bin;name;chrom;strand;txStart;txEnd;cdsStart;cdsEnd;exonCount;exonStarts;exonEnds;score;name2;cdsStartStat;cdsEndStat;exonFrames
        To a dictionary with refseqID as keys and he following list as the value:
            chromosome, strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, geneSymbol
        """
        ncbiRefSeq = dict()
        # ncbiRefSeq = list()
        with open(table_path.format(self.species), 'r') as refS:
            for line in refS:
                ll = line.strip().split('\t')
                ex_starts = [int(start) for start in ll[9].split(',') if len(start) > 0]
                ex_ends = [int(ends) for ends in ll[10].split(',') if len(ends) > 0]
                # ncbiRefSeq[ll[1]] = ncbiRefSeq.get(ll[1],
                #                                   [ll[2], ll[3]] + list(map(int, ll[4:9])) + [ex_starts, ex_ends,
                #                                                                               ll[12]])
                newT = Transcript(refseq=ll[1], ensembl=None, chrom=ll[2], strand=ll[3], tx=tuple(map(int, ll[4:6])),
                                  CDS=tuple(map(int, ll[6:8])), gene=ll[12], prot_refseq=None,
                                  protein_ensembl=None, exons_starts=ex_starts, exons_ends=ex_ends)
                ncbiRefSeq[ll[1]] = ncbiRefSeq.get(ll[1], newT)
        self.refseq = ncbiRefSeq

    def parse_kgXref(self, kgXref_path=os.getcwd() + '/data/{}/from_ucsc/kgXref.txt'):
        # kgID;mRNA;spID;spDisplayID;geneSymbol;refseq;protAcc;description;rfamAcc;tRnaName
        kgXref = {}
        with open(kgXref_path.format(self.species), 'r') as Xref:
            for line in Xref:
                ll = line.strip().split('\t')
                ll = [None if x == '' else x for x in ll]
                kgXref[ll[0]] = ll[1:]
        return kgXref

    def parse_knownGene(self, knownGene_path=os.getcwd() + '/data/{}/from_ucsc/knownGene.txt'):
        """
        Parse the knownGene table with the columns:
            name;chrom;strand;txStart;txEnd;cdsStart;cdsEnd;exonCount;exonStarts;exonEnds;proteinID;alignID
        To a dictionary with refseqID as keys and he following list as the value:
            chromosome, strand, txStart, txEnd, cdsStart, cdsEnd, exonCount, exonStarts, exonEnds, geneSymbol
        """
        kgXref = self.parse_kgXref()
        knownGene = dict()
        with open(knownGene_path.format(self.species), 'r') as known:
            for line in known:
                ll = line.strip().split('\t')
                ex_starts = [int(start) for start in ll[8].split(',') if len(start) > 0]
                ex_ends = [int(ends) for ends in ll[9].split(',') if len(ends) > 0]
                geneSymb = kgXref.get(ll[0], [None] * 4)[3]
                refseq = kgXref.get(ll[0], [None] * 5)[4]
                newT = Transcript(refseq=refseq, ensembl=ll[0], chrom=ll[1], strand=ll[2], tx=tuple(map(int, ll[3:5])),
                                  CDS=tuple(map(int, ll[5:7])), gene=geneSymb, prot_refseq=None,
                                  protein_ensembl=ll[10], exons_starts=ex_starts, exons_ends=ex_ends)
                knownGene[ll[0]] = knownGene.get(ll[0], newT)
        # self.aliases(knownGene, kgXref)
        self.ensembl = knownGene

    def parser(self):
        self.parse_ncbiRefSeq()
        self.parse_knownGene()
        combine = dict()
        added_id = set()
        for ref, trans in self.refseq.items():
            if trans.ensembl in self.ensembl.keys():
                merged = trans.mergeTranscripts(self.ensembl[trans.ensembl])
            else:
                merged = trans
            if ref not in added_id:
                if trans.ensembl not in added_id:
                    combine[(merged.refseq, merged.ensembl)] = merged
                    added_id.add(merged.refseq)
                    added_id.add(merged.ensembl)
                    added_id.remove(None)
                else:
                    raise ValueError("ref not in added id and ens in added id!!")
        for ens, trans in self.ensembl.items():
            if ens not in added_id:
                if trans.refseq not in added_id:
                    if trans.refseq in self.refseq.keys():
                        merged = trans.mergeTranscripts(self.refseq[trans.refseq])
                    else:
                        merged = trans
                else:
                    if (trans.refseq, ens) not in combine.keys():
                        raise ValueError(print("Inconsistent records!" +
                                               " current ensembl: {}".format(ens) +
                                               " (not in added_id), " +
                                               " linked refseq : {}".format(trans.refseq) +
                                               " (in added_id)." +
                                               "The ensembl of the record is : {}".format(
                                                   self.refseq[trans.refseq].ensembl)
                                               ))
                    else:
                        merged = combine[(trans.refseq, ens)]
                        merged = merged.mergeTranscripts(trans)
            combine[(trans.refseq, ens)] = merged
        self.combined = combine
