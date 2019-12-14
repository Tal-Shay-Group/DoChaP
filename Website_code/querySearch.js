const express = require("express");
const app = express.Router();
var DButils = require('./DButils');
var fs = require('fs');

//connects to the db using db module (DButils) and returns query answer
function sqlQuery(query) {
    var promise = new Promise(function (resolve, reject) {
        DButils.db.all(query, [], async (err, rows) => {
            if (err == undefined) {
                resolve(rows);
            } else {
                reject(err);
                console.log(err);
            }
        });
    });
    return promise;
}

// searches for exact gene name. if not found searches for synonyms. returns the record found
async function findGene(geneName, specie) {
    var ans = undefined;
    var sqlSpecie = "";
    if (specie != "all") {
        sqlSpecie = " AND (specie ='" + specie + "')";
    }
    var queryAns = await sqlQuery("SELECT gene_id , specie FROM Genes WHERE (UPPER(gene_symbol) = '" + geneName.toUpperCase() + "' or gene_id ='" + geneName + "')" + sqlSpecie);
    if (queryAns.length != 0) {
        return queryAns;
    } else {
        var geneByTranscriptOrProteinId = await sqlQuery("SELECT gene_id FROM Transcripts WHERE ( transcript_id='" + geneName + "' or protein_id='" + geneName + "')");
        if (geneByTranscriptOrProteinId.length > 0) {
            return geneByTranscriptOrProteinId;
        }
    }
    return undefined;
}

// for each transcripts looks for protein, exons, domains
async function findTranscriptInfo(transcript) {
    var transcriptExons = await sqlQuery("SELECT * FROM Transcript_Exon WHERE transcript_id =  '" + transcript.transcript_id + "'");
    transcript.transcriptExons = transcriptExons;

    var protein = await sqlQuery("SELECT * FROM Proteins WHERE transcript_id =  '" + transcript.transcript_id + "'");
    transcript.protein = protein[0];

    var domains = await sqlQuery("SELECT * FROM DomainEvent WHERE protein_id =  '" + transcript.protein_id + "'");
    transcript.domains = domains;

    var spliceInDomains = await sqlQuery("SELECT * FROM SpliceInDomains WHERE transcript_id =  '" + transcript.transcript_id + "'");
    transcript.spliceInDomains = spliceInDomains;

    //info on each domain
    for (var j = 0; j < transcript.domains.length; j++) {
        var domainType = await sqlQuery("SELECT * FROM DomainType WHERE type_id =  '" + transcript.domains[j].type_id + "'");
        transcript.domains[j].domainType = domainType[0];
    }
    return transcript;
}

//actual server handler. gets request and sends the final answer.
app.get("/querySearch/:inputGene/:specie/:isReviewed", async (req, res) => {
    var finalAns = {};
    var closeGene = "";
    var isExact = true;

    //finding gene
    finalAns.genes = await findGene(req.params.inputGene, req.params.specie);
    if (finalAns.genes == undefined) {
        if(req.params.inputGene.length>=4 && req.params.inputGene.substring(0,3)=='ENS'){
            closeGene = await emsemblRecords(req.params.inputGene, req.params.specie);
        }
        else {
            closeGene = await closeGenes(req.params.inputGene, req.params.specie);
        }
        
        if (closeGene.length == 0) {
            //send error
            res.status(400).send(finalAns);
            console.log("No Results Found");
            return;

        } else {
            if(closeGene.length>1){
                isExact = false;
            }
            finalAns.genes = closeGene;
        }

    }

    for (var i = 0; i < finalAns.genes.length; i++) {
        //get gene
        var gene = await sqlQuery("SELECT * FROM Genes WHERE gene_id =  '" + finalAns.genes[i].gene_id + "'");
        finalAns.genes[i] = gene[0];
        var sqlReviewed = "";
        if (req.params.isReviewed == "true") {
            sqlReviewed = " AND transcript_id LIKE 'NM%' ";
        }
        //get transcripts
        var transcripts = await sqlQuery("SELECT * FROM Transcripts WHERE gene_id =  '" + finalAns.genes[i].gene_id + "'" + sqlReviewed);
        finalAns.genes[i].transcripts = transcripts;

        //get exons
        var geneExons = await sqlQuery("SELECT * FROM Exons WHERE gene_id =  '" + finalAns.genes[i].gene_id + "'");
        finalAns.genes[i].geneExons = geneExons;

        //foreach transcript: protein, exons, domains
        for (var j = 0; j < finalAns.genes[i].transcripts.length; j++) {
            finalAns.genes[i].transcripts[j] = await findTranscriptInfo(finalAns.genes[i].transcripts[j]);
        }
    }
    //send ans
    finalAns.isExact = isExact;
    res.status(200).send(finalAns);

    console.log("querySearch:");
    console.log(finalAns);
    if (finalAns.genes != undefined && finalAns.genes.length > 0) {
        fs.writeFile("log.txt", "*res" + finalAns.genes[0].gene_id + "\n", {
            flag: 'a'
        }, function (err) {});
    }


});


async function closeGenes(geneName, specie) {
    if (geneName.substring(0, 2).toUpperCase() == "NM" ||
        geneName.substring(0, 2).toUpperCase() == "XM" ||
        geneName.substring(0, 2).toUpperCase() == "NP" ||
        geneName.substring(0, 2).toUpperCase() == "XP") {
        return closeProteins(geneName, specie);
    }
    var sqlSpecie = "";
    var synonyms = [];
    if (specie != "all") {
        sqlSpecie = " AND (specie ='" + specie + "')";
    }
    queryAns = await sqlQuery("SELECT gene_id , synonyms FROM Genes WHERE synonyms LIKE  '%" + geneName + "%'" + sqlSpecie);
    if (queryAns.length != 0) {
        for (var i = 0; i < queryAns.length; i++) {
            var geneSynonyms = queryAns[i].synonyms.split("; ");
            for (var j = 0; j < geneSynonyms.length; j++) {
                if (geneSynonyms[j].toLowerCase() == geneName.toLowerCase()) {
                    synonyms.push(queryAns[i]);


                }

            }
        }


    }
    return synonyms;
}

async function closeProteins(geneName, specie) {
    var sqlSpecie = "";
    if (specie != "all") {
        sqlSpecie = " AND (specie ='" + specie + "')";
    }
    var proteinNonVersion = geneName.split(".")[0].toUpperCase();
    queryAns = await sqlQuery("SELECT Genes.gene_id, specie " +
        "FROM (SELECT gene_id FROM Proteins WHERE protein_id LIKE '" + proteinNonVersion + "%') as tmp1" +
        ", Genes WHERE tmp1.gene_id=Genes.gene_id " + sqlSpecie);

    return queryAns;
}

async function emsemblRecords(geneName, specie) {
    var sqlSpecie = "";
    if (specie != "all") {
        sqlSpecie = " AND (specie ='" + specie + "')";
    }
    var recordNonVersion = geneName.split(".")[0].toUpperCase();
    queryAns1 = await sqlQuery("SELECT Genes.gene_id, specie " +
        "FROM (SELECT gene_id FROM Proteins WHERE ensembl_id LIKE '" + recordNonVersion + "%') as tmp1" +
        ", Genes WHERE tmp1.gene_id=Genes.gene_id " + sqlSpecie);
    queryAns2 = await sqlQuery("SELECT Genes.gene_id, specie " +
    "FROM (SELECT gene_id FROM Transcripts WHERE ensembl_ID LIKE '" + recordNonVersion + "%') as tmp1" +
    ", Genes WHERE tmp1.gene_id=Genes.gene_id " + sqlSpecie);
    if (queryAns1.length>0){
        return queryAns1;
    }
    return queryAns2;
}


module.exports = app;