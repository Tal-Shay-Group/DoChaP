/**
 * this file control gene searches and querying the database
 */

const express = require("express");
const app = express.Router();
var DButils = require('./DButils');
var Database = require('better-sqlite3');
var db = undefined;
var fs = require('fs');
var qCache = require('./QueryCache').qCache;



function sql(query, params) {
    return db.prepare(query).all(params);
}



//actual server handler. gets request and sends the final answer.
app.get("/querySearch/:inputGene/:specie/:isReviewed", async (req, res) => {
    db = new Database('DB_merged.sqlite');
    var finalAns = {};
    finalAns.isExact = true;
    var queryID = req.params.inputGene + "/" + req.params.specie + "/" + req.params.isReviewed;

    //check in cache
    var elementFromCache = qCache.getIfExists(queryID);
    if (elementFromCache != undefined) {
        //return to client
        res.status(200).send(elementFromCache);
        writeToLog(elementFromCache);
        return;
    }

    //find genes
    finalAns.genes = findGenes(req.params.inputGene);

    //try close genes 
    if (finalAns.genes == undefined) {
        finalAns.genes = closeGenes(req.params.inputGene);
        finalAns.isExact = false;
    }

    //filter by specie
    if (req.params.specie != 'all') {
        temp = []
        for (var i = 0; i < finalAns.genes.length; i++) {
            if (finalAns.genes[i].specie == req.params.specie) {
                temp.push(finalAns.genes[i]);
            }
        }
        finalAns.genes = temp;
    }


    //if nothing found
    if (finalAns.genes.length == 0) {
        res.status(200).send(finalAns);
        console.log("No Results Found");
        return;
    }

    //build gene info
    await buildGeneInfo(finalAns);

    //add to cache
    qCache.addNewQuery(queryID, finalAns);

    //send back to client
    res.status(200).send(finalAns);
    db.close();
    writeToLog(finalAns);
});

function writeToLog(finalAns) {
    console.log("querySearch:");
    console.log(finalAns);
    if (finalAns.genes != undefined && finalAns.genes.length > 0) {
        fs.writeFile("log.txt", "*res" + finalAns.genes[0].gene_GeneID_id + "\n", {
            flag: 'a'
        }, function (err) {});
    }

}
// searches for exact gene name. if not found searches for synonyms. returns the record found
function findGenes(geneName) {
    var ans = undefined;

    //search by gene_id/gene_symbol/ensembl_id
    ans = sql("SELECT gene_GeneID_id , specie FROM Genes WHERE (UPPER(gene_symbol) = ? or gene_GeneID_id = ? or gene_ensembl_id =?)", [geneName.toUpperCase(), geneName, geneName]);
    if (ans.length > 0) {
        return ans;
    }

    //search by refSeq transcript_id/protein_id
    ans = sql("SELECT Genes.gene_GeneID_id, specie " +
        "FROM (SELECT gene_GeneID_id FROM Transcripts WHERE transcript_refseq_id=? or transcript_ensembl_id=? or protein_refseq_id=? or protein_ensembl_id=?) as tmp1" +
        ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ", [geneName, geneName, geneName, geneName]);
    if (ans.length > 0) {
        return ans;
    }


    //search by refSeq with no version
    var recordNonVersion = geneName.split(".")[0].toUpperCase();
    ans = sql("SELECT Genes.gene_GeneID_id, specie " +
        "FROM (SELECT gene_GeneID_id FROM Transcripts WHERE transcript_refseq_id=? or protein_refseq_id=?) as tmp1" +
        ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ", [recordNonVersion, recordNonVersion]);
    if (ans.length > 0) {
        return ans;
    }

    // //search by other ID (they don't use versions)
    // var recordNonVersion = geneName.split(".")[0].toUpperCase();
    // ans = sql("SELECT Genes.gene_GeneID_id, specie " +
    //     "FROM (SELECT gene_GeneID_id FROM Proteins WHERE UPPER (ensembl_id) LIKE ?) as tmp1" +
    //     ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ",[recordNonVersion + '%']);
    // if (ans.length > 0) {
    //     return ans;
    // }
    // ans = sql("SELECT Genes.gene_GeneID_id, specie " +
    //     "FROM (SELECT gene_GeneID_id FROM Transcripts WHERE UPPER(ensembl_ID) LIKE ?) as tmp1" +
    //     ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ",[recordNonVersion + '%']);
    // if (ans.length > 0) {
    //     return ans;
    // }
    // ans = sql("SELECT Genes.gene_GeneID_id, specie " +
    //     "FROM (SELECT gene_GeneID_id FROM Proteins WHERE UPPER(uniprot_id) LIKE ?) as tmp1" +
    //     ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ",[recordNonVersion + '%']);
    // if (ans.length > 0) {
    //     return ans;
    // }

    //search by refSeq transcript_id/protein_id WITH NO VERSIONS
    // ans = sql("SELECT Genes.gene_GeneID_id, specie " +
    //     "FROM (SELECT gene_GeneID_id FROM Proteins WHERE protein_id LIKE ?) as tmp1" +
    //     ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ",[recordNonVersion + '%']);
    // if (ans.length > 0) {
    //     return ans;
    // }

    // ans = sql("SELECT Genes.gene_GeneID_id, specie " +
    //     "FROM (SELECT gene_GeneID_id FROM Transcripts WHERE transcript_id LIKE ?) as tmp1" +
    //     ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ",[recordNonVersion + '%']);
    // if (ans.length > 0) {
    //     return ans;
    // }
    return undefined;
}

// for each transcripts looks for protein, exons, domains
async function findTranscriptInfo(transcript) {
    var transcriptExons = sql("SELECT * FROM Transcript_Exon WHERE transcript_refseq_id =  ? or transcript_ensembl_id = ?", [transcript.transcript_refseq_id, transcript.transcript_ensembl_id]);
    transcript.transcriptExons = transcriptExons;
    var protein = sql("SELECT * FROM Proteins WHERE transcript_refseq_id =  ? or transcript_ensembl_id = ?", [transcript.transcript_refseq_id, transcript.transcript_ensembl_id]);
    transcript.protein = protein[0];
    var domains = sql("SELECT * FROM DomainEvent WHERE protein_refseq_id = ? or protein_ensembl_id = ?", [transcript.protein_refseq_id, transcript.protein_ensembl_id]);
    transcript.domains = domains;

    // var spliceInDomains = sql("SELECT * FROM SpliceInDomains WHERE transcript_refseq_id = ? or transcript_ensembl_id = ?",[transcript.transcript_refseq_id,transcript.transcript_refseq_id]);
    // transcript.spliceInDomains = spliceInDomains;
    //info on each domain
    for (var j = 0; j < transcript.domains.length; j++) {
        var domainType = sql("SELECT * FROM DomainType WHERE type_id = ?", [transcript.domains[j].type_id]);
        transcript.domains[j].domainType = domainType[0];
    }
    return transcript;
}


//if regular search does not work we find genes that are similar 
//because the user may have wanted them and searched for something wrong
function closeGenes(geneName) {
    //find synonyms
    var synonyms = [];
    ans = sql("SELECT gene_ensembl_id, gene_GeneID_id, specie, synonyms,gene_symbol FROM Genes WHERE (synonyms LIKE ? OR synonyms LIKE ?)", [geneName + '%', '%; ' + geneName + '%']);
    if (ans.length != 0) {
        for (var i = 0; i < ans.length; i++) {
            var geneSynonyms = ans[i].synonyms.split("; ");
            for (var j = 0; j < geneSynonyms.length; j++) {
                if (geneSynonyms[j].toLowerCase() == geneName.toLowerCase()) {
                    synonyms.push(ans[i]);
                }
            }
        }
    }
    return synonyms;

}

async function buildGeneInfo(finalAns) {
    //after finding the genes, completing all information needed for results
    for (var i = 0; i < finalAns.genes.length; i++) {
        //get gene
        var gene = sql("SELECT * FROM Genes WHERE gene_GeneID_id = ?", [finalAns.genes[i].gene_GeneID_id]);
        finalAns.genes[i] = gene[0]; //first and only one who matches this id

        //get transcripts
        var transcripts = sql("SELECT * FROM Transcripts WHERE gene_GeneID_id = ?", [finalAns.genes[i].gene_GeneID_id]);
        finalAns.genes[i].transcripts = transcripts;

        //get exons
        var geneExons = sql("SELECT * FROM Exons WHERE gene_GeneID_id = ?", [finalAns.genes[i].gene_GeneID_id]);
        finalAns.genes[i].geneExons = geneExons;

        //foreach transcript: protein, exons, domains
        // for (var j = 0; j < finalAns.genes[i].transcripts.length; j++) {
        //     finalAns.genes[i].transcripts[j] = await findTranscriptInfo(finalAns.genes[i].transcripts[j]);

        // }
        await Promise.all(finalAns.genes[i].transcripts.map(async (transcript, index) => {
            finalAns.genes[i].transcripts[index] = await findTranscriptInfo(transcript)
        }))
    }
}

//get orthology
app.get('/getOrthologyGenes/:species/:gene', (req, res) => {
    db = new Database('DB_merged.sqlite');
    console.log('Orthology');
    var gene = req.params.gene.toUpperCase();
    var species = req.params.species;
    // var results = sql("SELECT * FROM Orthology WHERE UPPER( "+species+"_name"+" ) LIKE ? ",["%"+gene+"%"]);

    //check A
    var results = sql("SELECT * FROM Orthology WHERE (UPPER( A_ensembl_id ) = ? or UPPER( A_GeneSymb ) =? ) AND A_Species = ?", [gene, gene, species]);
    if (results.length > 0) {
        res.status(200).send(results);
        db.close();
        return;
    }

    //check B
    results = sql("SELECT * FROM Orthology WHERE (UPPER( B_ensembl_id ) = ? or UPPER( B_GeneSymb ) =? ) AND B_Species = ?", [gene, gene, species]);
    if (results.length > 0) {
        res.status(200).send(results);
        db.close();
        return;
    }
    results = closeGenes(gene);
    if (results.length > 0) {
        var found = undefined;
        for (var i = 0; i < results.length; i++) {
            if (results[i].specie == species) {
                found = results[i];
            }
        }
        if (found == undefined) {
            res.status(200).send([]);
            db.close();
            return;
        } else {
            gene=found.gene_symbol.toUpperCase();
            console.log(gene);
            //check A
            results = sql("SELECT * FROM Orthology WHERE (UPPER( A_ensembl_id ) = ? or UPPER( A_GeneSymb ) =? ) AND A_Species = ?", [gene, gene, species]);
            if (results.length > 0) {
                res.status(200).send(results);
                console.log("res"+results);
                db.close();
                return;
            }

            //check B
            results = sql("SELECT * FROM Orthology WHERE (UPPER( B_ensembl_id ) = ? or UPPER( B_GeneSymb ) =? ) AND B_Species = ?", [gene, gene, species]);
            if (results.length > 0) {
                res.status(200).send(results);
                db.close();
                return;
            }

            res.status(200).send([]);
            db.close();
            return;
        }
    }

    db.close();
    res.status(200).send([]);
});

module.exports = app;