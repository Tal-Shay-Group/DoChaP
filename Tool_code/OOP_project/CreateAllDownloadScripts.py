import sys
import os

sys.path.append(os.getcwd())
from OrthologsBuilder import OrthologsBuilder
from DomainsEnsemblBuilder import DomainsEnsemblBuilder


def Add2ShellDownloads(Builder, file):
    Builder.returnShellScripts(tofile=file)


if __name__ == "__main__":
    species = ('M_musculus', 'H_sapiens', 'R_norvegicus', 'D_rerio', 'X_tropicalis')
    writeFile = os.getcwd() + "/ShellScripts.txt"
    Add2ShellDownloads(OrthologsBuilder(), writeFile)
    for sp in species:
        shellBuilders = [DomainsEnsemblBuilder(sp)]
        for builder in shellBuilders:
            Add2ShellDownloads(builder, writeFile)


