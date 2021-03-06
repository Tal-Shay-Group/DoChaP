import sys
import os

sys.path.append(os.getcwd())
from Director import Director
from IDconverterBuilder import ConverterBuilder
from gffRefseqBuilder import RefseqBuilder
from gffEnsemblBuilder import EnsemblBuilder
from InterproCollector import InterProBuilder
# from conf import all_species
# from OrthologsBuilder import OrthologsBuilder
# from DomainsEnsemblBuilder import DomainsEnsemblBuilder


def CallDownloader(Builder):
    director = Director()
    director.setBuilder(Builder)
    director.collectFromSource(download=True, parser=False)


if __name__ == "__main__":
    all_species = ["R_norvegicus"]
    for sp in all_species:
        if sp == "X_tropicalis" or sp == "R_norvegicus":
            #  18/2/21 - only use refseq data for Xenopus_tropicalis untill refseq and ensembl genome versions will match.
            downloadBuilders = [RefseqBuilder(sp), ConverterBuilder(sp)]
        else:
            downloadBuilders = [RefseqBuilder(sp), EnsemblBuilder(sp), ConverterBuilder(sp)]
        for builder in downloadBuilders:
            CallDownloader(builder)
    #CallDownloader(InterProBuilder())
