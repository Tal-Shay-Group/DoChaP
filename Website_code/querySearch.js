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

/*


var stmt = db.prepare('SELECT * FROM users WHERE id=?');
var row = stmt.get(userId);
console.log(row.name, row.email);

*/


function sql(query,params) {
    return db.prepare(query).all(params);
}



//actual server handler. gets request and sends the final answer.
app.get("/querySearch/:inputGene/:specie/:isReviewed", async (req, res) => {
    db=new Database('DB_merged.sqlite');
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
    finalAns.genes = await findGenes(req.params.inputGene);
    
    //try close genes 
    if (finalAns.genes == undefined) {
        finalAns.genes = await closeGenes(req.params.inputGene);
        finalAns.isExact = false;
    }

    //filter by specie
    if (req.params.specie!='all'){
        temp=[]
        for (var i=0; i<finalAns.genes.length;i++ ){
            if(finalAns.genes[i].specie==req.params.specie){
                temp.push(finalAns.genes[i]);
            }
        }
        finalAns.genes=temp;
    }
    

    //if nothing found
    if (finalAns.genes.length == 0 ) {
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

function writeToLog(finalAns){
    console.log("querySearch:");
    console.log(finalAns);
    if (finalAns.genes != undefined && finalAns.genes.length > 0) {
        fs.writeFile("log.txt", "*res" + finalAns.genes[0].gene_id + "\n", {
            flag: 'a'
        }, function (err) {});
    }

}
// searches for exact gene name. if not found searches for synonyms. returns the record found
async function findGenes(geneName) {
    var ans = undefined;

    //search by gene_id/gene_symbol/ensembl_id
    ans = sql("SELECT gene_id , specie FROM Genes WHERE (UPPER(gene_symbol) = ? or gene_id = ? or ensembl_id =?)",[geneName.toUpperCase(),geneName,geneName]);
    if (ans.length > 0) {
        return ans;
    }

    //search by refSeq transcript_id/protein_id
    ans = sql("SELECT Genes.gene_id, specie " +
        "FROM (SELECT gene_id FROM Transcripts WHERE transcript_id=? or protein_id=?) as tmp1" +
        ", Genes WHERE tmp1.gene_id=Genes.gene_id ",[geneName,geneName]);
    if (ans.length > 0) {
        return ans;
    }

    //search by other ID (they don't use versions)
    var recordNonVersion = geneName.split(".")[0].toUpperCase();
    ans = sql("SELECT Genes.gene_id, specie " +
        "FROM (SELECT gene_id FROM Proteins WHERE UPPER (ensembl_id) LIKE ?) as tmp1" +
        ", Genes WHERE tmp1.gene_id=Genes.gene_id ",[recordNonVersion + '%']);
    if (ans.length > 0) {
        return ans;
    }
    ans = sql("SELECT Genes.gene_id, specie " +
        "FROM (SELECT gene_id FROM Transcripts WHERE UPPER(ensembl_ID) LIKE ?) as tmp1" +
        ", Genes WHERE tmp1.gene_id=Genes.gene_id ",[recordNonVersion + '%']);
    if (ans.length > 0) {
        return ans;
    }
    ans = sql("SELECT Genes.gene_id, specie " +
        "FROM (SELECT gene_id FROM Proteins WHERE UPPER(uniprot_id) LIKE ?) as tmp1" +
        ", Genes WHERE tmp1.gene_id=Genes.gene_id ",[recordNonVersion + '%']);
    if (ans.length > 0) {
        return ans;
    }

    //search by refSeq transcript_id/protein_id WITH NO VERSIONS
    ans = sql("SELECT Genes.gene_id, specie " +
        "FROM (SELECT gene_id FROM Proteins WHERE protein_id LIKE ?) as tmp1" +
        ", Genes WHERE tmp1.gene_id=Genes.gene_id ",[recordNonVersion + '%']);
    if (ans.length > 0) {
        return ans;
    }

    ans = sql("SELECT Genes.gene_id, specie " +
        "FROM (SELECT gene_id FROM Transcripts WHERE transcript_id LIKE ?) as tmp1" +
        ", Genes WHERE tmp1.gene_id=Genes.gene_id ",[recordNonVersion + '%']);
    if (ans.length > 0) {
        return ans;
    }

    return undefined;
}

// for each transcripts looks for protein, exons, domains
async function findTranscriptInfo(transcript) {
    var transcriptExons = sql("SELECT * FROM Transcript_Exon WHERE transcript_id =  ?",[transcript.transcript_id]);
    transcript.transcriptExons = transcriptExons;

    var protein = sql("SELECT * FROM Proteins WHERE transcript_id = ?",[transcript.transcript_id]);
    transcript.protein = protein[0];

    var domains = sql("SELECT * FROM DomainEvent WHERE protein_id = ?",[transcript.protein_id]);
    transcript.domains = domains;

    var spliceInDomains = sql("SELECT * FROM SpliceInDomains WHERE transcript_id = ?",[transcript.transcript_id]);
    transcript.spliceInDomains = spliceInDomains;

    //info on each domain
    for (var j = 0; j < transcript.domains.length; j++) {
        var domainType = sql("SELECT * FROM DomainType WHERE type_id = ?",[transcript.domains[j].type_id]);
        transcript.domains[j].domainType = domainType[0];
    }
    return transcript;
}


//if regular search does not work we find genes that are similar 
//because the user may have wanted them and searched for something wrong
async function closeGenes(geneName) {
    //find synonyms
    var synonyms = [];
    ans = await sql("SELECT gene_id, specie, synonyms FROM Genes WHERE (synonyms LIKE ? OR synonyms LIKE ?)",[ geneName+'%', '%; '+geneName+'%']);
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

async function buildGeneInfo(finalAns){
    
    //after finding the genes, completing all information needed for results
    for (var i = 0; i < finalAns.genes.length; i++) {
        //get gene
        var gene = sql("SELECT * FROM Genes WHERE gene_id = ?",[finalAns.genes[i].gene_id]);
        finalAns.genes[i] = gene[0]; //first and only one who matches this id

        //get transcripts
        var transcripts = sql("SELECT * FROM Transcripts WHERE gene_id = ?",[finalAns.genes[i].gene_id]);
        finalAns.genes[i].transcripts = transcripts;
        
        //get exons
        var geneExons = sql("SELECT * FROM Exons WHERE gene_id = ?",[finalAns.genes[i].gene_id]);
        finalAns.genes[i].geneExons = geneExons;

        //foreach transcript: protein, exons, domains
        for (var j = 0; j < finalAns.genes[i].transcripts.length; j++) {
            finalAns.genes[i].transcripts[j] = await findTranscriptInfo(finalAns.genes[i].transcripts[j]);
        }
    }
}


//connects to the db using db module (DButils) and returns query answer
/*function sqlQuery(query) {
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
}*/

module.exports = app;