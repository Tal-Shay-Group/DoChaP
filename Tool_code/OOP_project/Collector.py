from Director import *
from ffBuilder import *
from UcscBuilder import *
import ensemblBuilder
import OrthologsBuilder
import IDconverterBuilder


class Collector:

    def __init__(self, species):
        self.species = species
        self.ucsc = UcscBuilder(species)
        self.ff = ffBuilder(species)

    def collectAll(self):
        director = Director()
        director.setBuilder(self.ucsc)
        refGene, ucsc_acc = director.collectFromSource()

    #director.setBuilder(ffbuilder)
    # ff = director.collectFromSource()

    # download_refseq_ensemble_connection()
    #region_dict, p_info, g_info, pro2gene, gene2pro, all_domains, kicked = director.collectFromSource()
    #gene_con, trans_con, protein_con = gene2ensembl_parser(species)