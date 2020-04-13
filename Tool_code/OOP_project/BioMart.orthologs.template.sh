#!/bin/sh

wget -O output.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "0" uniqueRows = "0" count = "" datasetConfigVersion = "0.6" >
			
	<Dataset name = "MainSpecies" interface = "default" >
		<Attribute name = "ensembl_gene_id" />
		<Attribute name = "ensembl_transcript_id" />
		<Attribute name = "Comp1_homolog_ensembl_gene" />
		<Attribute name = "Comp1_homolog_associated_gene_name" />
		<Attribute name = "Comp1_homolog_ensembl_peptide" />
		<Attribute name = "Comp1_homolog_orthology_type" />
		<Attribute name = "Comp2_homolog_ensembl_gene" />
		<Attribute name = "Comp2_homolog_associated_gene_name" />
		<Attribute name = "Comp2_homolog_ensembl_peptide" />
		<Attribute name = "Comp2_homolog_orthology_type" />
		<Attribute name = "Comp3_homolog_ensembl_gene" />
		<Attribute name = "Comp3_homolog_associated_gene_name" />
		<Attribute name = "Comp3_homolog_ensembl_peptide" />
		<Attribute name = "Comp3_homolog_orthology_type" />
		<Attribute name = "Comp4_homolog_ensembl_gene" />
		<Attribute name = "Comp4_homolog_associated_gene_name" />
		<Attribute name = "Comp4_homolog_ensembl_peptide" />
		<Attribute name = "Comp4_homolog_orthology_type" />
		<Attribute name = "external_gene_name" />
		<Attribute name = "ensembl_peptide_id" />
	</Dataset>
</Query>'