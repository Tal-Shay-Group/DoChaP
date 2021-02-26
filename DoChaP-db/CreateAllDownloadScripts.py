import sys
import os

sys.path.append(os.getcwd())
from OrthologsBuilder import OrthologsBuilder
from DomainsEnsemblBuilder import DomainsEnsemblBuilder
from conf import all_species


def Add2ShellDownloads(Builder, file):
    Builder.returnShellScripts(toFile=file)


if __name__ == "__main__":
    writeFile = os.getcwd() + "/ShellScripts.txt"
    writo = open(writeFile, "w")
    writo.close()
    Add2ShellDownloads(OrthologsBuilder(), writeFile)
    for sp in all_species:
        shellBuilders = [DomainsEnsemblBuilder(sp)]
        for builder in shellBuilders:
            Add2ShellDownloads(builder, writeFile)


