#!/bin/sh

wget -O output.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >
			
	<Dataset name = "MainSpecies" interface = "default" >
		<Attribute name = "ensembl_gene_id" />
		<Attribute name = "external_gene_name" />
		<Attribute name = "Comp1_homolog_ensembl_gene" />
		<Attribute name = "Comp1_homolog_associated_gene_name" />
		<Attribute name = "Comp1_homolog_orthology_type" />
	</Dataset>
</Query>'