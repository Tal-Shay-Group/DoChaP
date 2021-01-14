class Director:
    __builder = None

    def setBuilder(self, builder):
        self.__builder = builder
        # self.__builder.setSpecies(species)

    def collectFromSource(self, download=False, parser=True):
        if download:
            self.__builder.downloader
        if parser:
            self.__builder.parser()
        # return self.__builder.records()


# Builder
class SourceBuilder:
    """
    Specify methods for all the classes to handle specific data sources
    """

    def __init__(self, species):
        self.species = species

    def downloader(self):
        pass

    def parser(self):
        pass
