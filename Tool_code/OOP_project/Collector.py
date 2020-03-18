from Director import *
from ffBuilder import *
from UcscBuilder import *
import ensemblBuilder
import OrthologsBuilder
import IDconverterBuilder

from OOP_project.Director import Director
from OOP_project.UcscBuilder import UcscBuilder
from OOP_project.ffBuilder import ffBuilder
from OOP_project.IDconverterBuilder import ConverterBuilder


class Collector:

    def __init__(self, species):
        self.species = species
        self.director = Director()
        self.ucsc_acc = []
        self.ff = None
        self.gene2ensembl = None

    def collectAll(self):

        ucsc = UcscBuilder(self.species)
        self.director.setBuilder(ucsc)
        self.director.collectFromSource()

        ff = ffBuilder(self.species)
        self.director.setBuilder(ff)
        self.director.collectFromSource()

        idConv = ConverterBuilder(self.species)
        self.director.setBuilder(idConv)
        self.director.collectFromSource()

    #director.setBuilder(ffbuilder)
    # ff = director.collectFromSource()

    # download_refseq_ensemble_connection()
    #region_dict, p_info, g_info, pro2gene, gene2pro, all_domains, kicked = director.collectFromSource()
    #gene_con, trans_con, protein_con = gene2ensembl_parser(species)