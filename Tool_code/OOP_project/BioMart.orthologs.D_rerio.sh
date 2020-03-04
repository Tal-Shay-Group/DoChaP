#!/bin/sh

wget -O D_rerio.orthology.txt 'http://www.ensembl.org/biomart/martservice?query=<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Query>
<Query  virtualSchemaName = "default" formatter = "TSV" header = "0" uniqueRows = "0" count = "" datasetConfigVersion = "0.6" >
			
<<<<<<< HEAD
	<Dataset name = "drerio_gene_ensembl" interface = "default" >
=======
	<Dataset name = "drerio" interface = "default" >
>>>>>>> faa25599fa82255e0a33bdf1f7e726929074c2b2
		<Attribute name = "ensembl_gene_id" />
		<Attribute name = "ensembl_transcript_id" />
		<Attribute name = "mmusculus_homolog_ensembl_gene" />
		<Attribute name = "mmusculus_homolog_associated_gene_name" />
		<Attribute name = "mmusculus_homolog_ensembl_peptide" />
		<Attribute name = "mmusculus_homolog_orthology_type" />
<<<<<<< HEAD
=======
		<Attribute name = "hsapiens_homolog_ensembl_gene" />
		<Attribute name = "hsapiens_homolog_associated_gene_name" />
		<Attribute name = "hsapiens_homolog_ensembl_peptide" />
		<Attribute name = "hsapiens_homolog_orthology_type" />
>>>>>>> faa25599fa82255e0a33bdf1f7e726929074c2b2
		<Attribute name = "xtropicalis_homolog_ensembl_gene" />
		<Attribute name = "xtropicalis_homolog_associated_gene_name" />
		<Attribute name = "xtropicalis_homolog_ensembl_peptide" />
		<Attribute name = "xtropicalis_homolog_orthology_type" />
		<Attribute name = "rnorvegicus_homolog_ensembl_gene" />
		<Attribute name = "rnorvegicus_homolog_associated_gene_name" />
		<Attribute name = "rnorvegicus_homolog_ensembl_peptide" />
<<<<<<< HEAD
		<Attribute name = "rnorvegicus_homolog_orthology_type" />
		<Attribute name = "hsapiens_homolog_ensembl_gene" />
		<Attribute name = "hsapiens_homolog_associated_gene_name" />
		<Attribute name = "hsapiens_homolog_ensembl_peptide" />
		<Attribute name = "hsapiens_homolog_orthology_type" />
=======
		<Attribute name = "rnorvegicus_orthology_type" />
>>>>>>> faa25599fa82255e0a33bdf1f7e726929074c2b2
		<Attribute name = "external_gene_name" />
		<Attribute name = "ensembl_peptide_id" />
	</Dataset>
</Query>'