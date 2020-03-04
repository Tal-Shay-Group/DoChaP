#!/bin/sh

wget -O results.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "0" uniqueRows = "0" count = "" datasetConfigVersion = "0.6" >
			
	<Dataset name = "hsapiens_gene_ensembl" interface = "default" >
		<Attribute name = "ensembl_gene_id" />
		<Attribute name = "ensembl_transcript_id" />
		<Attribute name = "mmusculus_homolog_ensembl_gene" />
		<Attribute name = "mmusculus_homolog_associated_gene_name" />
		<Attribute name = "mmusculus_homolog_ensembl_peptide" />
		<Attribute name = "mmusculus_homolog_orthology_type" />
		<Attribute name = "drerio_homolog_ensembl_gene" />
		<Attribute name = "drerio_homolog_associated_gene_name" />
		<Attribute name = "drerio_homolog_ensembl_peptide" />
		<Attribute name = "drerio_homolog_orthology_type" />
		<Attribute name = "rnorvegicus_homolog_ensembl_gene" />
		<Attribute name = "rnorvegicus_homolog_associated_gene_name" />
		<Attribute name = "rnorvegicus_homolog_ensembl_peptide" />
		<Attribute name = "rnorvegicus_homolog_orthology_type" />
		<Attribute name = "xtropicalis_homolog_ensembl_gene" />
		<Attribute name = "xtropicalis_homolog_associated_gene_name" />
		<Attribute name = "xtropicalis_homolog_ensembl_peptide" />
		<Attribute name = "xtropicalis_homolog_orthology_type" />
		<Attribute name = "external_gene_name" />
		<Attribute name = "ensembl_peptide_id" />
	</Dataset>
</Query>'
