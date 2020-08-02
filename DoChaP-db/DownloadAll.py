import sys
import os

sys.path.append(os.getcwd())
from Director import Director
from IDconverterBuilder import ConverterBuilder
from gffRefseqBuilder import RefseqBuilder
from gffEnsemblBuilder import EnsemblBuilder
from InterproCollector import InterProBuilder
from OrthologsBuilder import OrthologsBuilder
from DomainsEnsemblBuilder import DomainsEnsemblBuilder

def CallDownloader(Builder):
        director = Director()
        director.setBuilder(Builder)
        director.collectFromSource(download = True, parser = False)


if __name__ == "__main__":
    species = ('M_musculus', 'H_sapiens', 'R_norvegicus', 'D_rerio', 'X_tropicalis')
    for sp in species:
        downloadBuilders = [RefseqBuilder(sp), EnsemblBuilder(sp), ConverterBuilder(sp)]
        for builder in downloadBuilders:
            CallDownloader(builder)
    CallDownloader(InterProBuilder())
