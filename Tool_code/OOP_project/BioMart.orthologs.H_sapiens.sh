#!/bin/sh

wget -O C:\Users\galozs\OneDrive\PhD\Projects\DoChaP\DoChaP\Tool_code\OOP_project/data/orthology/H_sapiens.orthology.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "1" uniqueRows = "1" count = "" datasetConfigVersion = "0.6" >
			
	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
		<Attribute name = "ensembl_gene_id" />
		<Attribute name = "mmusculus_homolog_ensembl_gene" />
		<Attribute name = "mmusculus_homolog_associated_gene_name" />
		<Attribute name = "mmusculus_homolog_orthology_type" />
		<Attribute name = "rnorvegicus_homolog_ensembl_gene" />
		<Attribute name = "rnorvegicus_homolog_associated_gene_name" />
		<Attribute name = "rnorvegicus_homolog_orthology_type" />
		<Attribute name = "drerio_homolog_ensembl_gene" />
		<Attribute name = "drerio_homolog_associated_gene_name" />
		<Attribute name = "drerio_homolog_orthology_type" />
		<Attribute name = "xtropicalis_homolog_ensembl_gene" />
		<Attribute name = "xtropicalis_homolog_associated_gene_name" />
		<Attribute name = "xtropicalis_homolog_orthology_type" />
		<Attribute name = "external_gene_name" />
	</Dataset>
</Query>'
