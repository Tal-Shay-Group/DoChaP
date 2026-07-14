/**
 * this file control gene searches and querying the database
 */

const express = require("express");
const app = express.Router();
var Database = require('better-sqlite3');
// single long-lived connection. better-sqlite3 is synchronous, so one shared
// connection is safe; opening/closing per request races across async handlers
// (one request's db.close() pulls the handle out from under another) and crashes
// the process.
var db = new Database('DB_merged.sqlite');
var fs = require('fs');
const { json } = require("express");
var qCache = require('./QueryCache').qCache;

//sql to db
function sql(query, params) {
    return db.prepare(query).all(params);
}


//actual server handler. gets request and sends the final answer.
// useRepDomains is optional and defaults to unset/false, preserving the original
// DomainEvent/DomainType-only behavior for every existing caller/URL.
app.get("/querySearch/:inputGene/:specie/:isReviewed/:useRepDomains?", async (req, res) => {
    var finalAns = {};
    finalAns.isExact = true;
    var useRepDomains = req.params.useRepDomains === "true";
    var queryID = req.params.inputGene + "/" + req.params.specie + "/" + req.params.isReviewed + "/" + useRepDomains;

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
    await buildGeneInfo(finalAns, useRepDomains);

    //add to cache
    qCache.addNewQuery(queryID, finalAns);

    //send back to client
    res.status(200).send(finalAns);
    writeToLog(finalAns);
});

//writes to log the result
function writeToLog(finalAns) {
    console.log("querySearch:");
    console.log(finalAns);
    if (finalAns.genes != undefined && finalAns.genes.length > 0) {
        fs.writeFile("log.txt",new Date().toLocaleString() +","+finalAns.genes[0].gene_GeneID_id + "\r\n", {
            flag: 'a'
        }, function (err) {});
    }

}

// searches for exact gene name. if not found searches for synonyms. returns the record found
function findGenes(geneName) {
    var ans = undefined;
    //search by gene_id/gene_symbol/ensembl_id
    ans = sql("SELECT gene_GeneID_id , specie FROM Genes WHERE (UPPER(gene_symbol) = ? or UPPER(gene_GeneID_id) = ? or UPPER(gene_ensembl_id) =?)", [geneName.toUpperCase(), geneName.toUpperCase(), geneName.toUpperCase()]);
    if (ans.length > 0) {
        return ans;
    }

    //search by refSeq transcript_id/protein_id
    ans = sql("SELECT Genes.gene_GeneID_id, specie " +
        "FROM (SELECT gene_GeneID_id FROM Transcripts WHERE UPPER(transcript_refseq_id)=? or UPPER(transcript_ensembl_id)=? or UPPER(protein_refseq_id)=? or UPPER(protein_ensembl_id)=?) as tmp1" +
        ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ", [geneName.toUpperCase(), geneName.toUpperCase(), geneName.toUpperCase(), geneName.toUpperCase()]);
    if (ans.length > 0) {
        return ans;
    }

    //search by refSeq/Ensembl with no version
    var recordNonVersion = geneName.split(".")[0].toUpperCase();
    ans = sql("SELECT Genes.gene_GeneID_id, specie " +
        "FROM (SELECT gene_GeneID_id FROM Transcripts WHERE UPPER(transcript_refseq_id) LIKE ? or UPPER(protein_refseq_id)LIKE ? or UPPER(protein_ensembl_id)LIKE ? or UPPER(protein_ensembl_id)LIKE ?) as tmp1" +
        ", Genes WHERE tmp1.gene_GeneID_id=Genes.gene_GeneID_id ", [recordNonVersion+ '%', recordNonVersion+ '%', recordNonVersion+ '%', recordNonVersion+ '%']);
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

// domains for a protein straight from DomainEvent/DomainType, in the shape the
// front-end Domain model (client/modules/Domain.js) expects.
function getDomainEventDomains(protein_refseq_id, protein_ensembl_id) {
    var domains = sql("SELECT type_id,AA_start,AA_end,nuc_start,nuc_end,ext_id FROM DomainEvent WHERE protein_refseq_id = ? or protein_ensembl_id = ?", [protein_refseq_id, protein_ensembl_id]);
    for (var j = 0; j < domains.length; j++) {
        var domainType = sql("SELECT type_id,name, other_name FROM DomainType WHERE type_id = ?", [domains[j].type_id]);
        domains[j].domainType = domainType[0];
    }
    return domains;
}

// domains for a protein from the RepresentativeDomains table (populated by
// DoChaP-db/InterProRepresentativeDomains.py), reshaped into the same
// {AA_start, AA_end, nuc_start, nuc_end, ext_id, domainType} shape as
// getDomainEventDomains() so the rest of the client code doesn't need to change.
// RepresentativeDomains only stores AA (protein) positions; nuc_start/nuc_end
// (CDS-relative nucleotide positions, 1-indexed) are derived the same way
// DomainEvent's own nuc_start/nuc_end relate to its AA_start/AA_end.
function getRepresentativeDomains(protein_interpro_id) {
    if (!protein_interpro_id) {
        return [];
    }
    try {
        var rows = sql("SELECT domain_id, domain_name, start, end FROM RepresentativeDomains WHERE protein_id = ? ORDER BY start", [protein_interpro_id]);
    } catch (err) {
        // RepresentativeDomains table not present in this DB - fall back to DomainEvent.
        return [];
    }
    return rows.map(function (row) {
        // Domain.getName() falls back to ext_id only when name/other_name are undefined,
        // so an empty domain_name (e.g. some Gene3D accessions) must stay undefined here
        // rather than "" - otherwise the tooltip would show a blank name instead of falling back.
        var name = row.domain_name && row.domain_name.trim() ? row.domain_name : undefined;
        return {
            type_id: row.domain_id,
            AA_start: row.start,
            AA_end: row.end,
            nuc_start: (row.start - 1) * 3 + 1,
            nuc_end: row.end * 3,
            ext_id: row.domain_id,
            domainType: { type_id: row.domain_id, name: name, other_name: undefined },
        };
    });
}

// for each transcripts looks for protein, exons, domains
// useRepDomains=false (default): unchanged - domains always come from
// DomainEvent/DomainType.
// useRepDomains=true: domains come from RepresentativeDomains when the protein
// has an entry there, falling back to DomainEvent/DomainType otherwise.
async function findTranscriptInfo(transcript, useRepDomains) {
    var transcriptExons = await new Promise((resolve, reject) => {
        resolve(sql("SELECT order_in_transcript, genomic_start_tx, genomic_end_tx, abs_start_CDS, abs_end_Cds FROM Transcript_Exon WHERE transcript_refseq_id =  ? or transcript_ensembl_id = ?", [transcript.transcript_refseq_id, transcript.transcript_ensembl_id]));
      });
    transcript.transcriptExons = transcriptExons;
    var protein = sql("SELECT * FROM Proteins WHERE transcript_refseq_id =  ? or transcript_ensembl_id = ?", [transcript.transcript_refseq_id, transcript.transcript_ensembl_id]);
    transcript.protein = protein[0];

    var domains = undefined;
    if (useRepDomains && transcript.protein != undefined) {
        domains = getRepresentativeDomains(transcript.protein.protein_interpro_id);
    }
    if (domains == undefined || domains.length == 0) {
        domains = getDomainEventDomains(transcript.protein_refseq_id, transcript.protein_ensembl_id);
    }
    transcript.domains = domains;
    // var spliceInDomains = sql("SELECT * FROM SpliceInDomains WHERE transcript_refseq_id = ? or transcript_ensembl_id = ?",[transcript.transcript_refseq_id,transcript.transcript_refseq_id]);
    // transcript.spliceInDomains = spliceInDomains;

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

//when has gene than we get all information from all related tables
async function buildGeneInfo(finalAns, useRepDomains) {
    //after finding the genes, completing all information needed for results
    for (var i = 0; i < finalAns.genes.length; i++) {
        //get gene
        var gene = sql("SELECT * FROM Genes WHERE gene_GeneID_id = ?", [finalAns.genes[i].gene_GeneID_id]);
        finalAns.genes[i] = gene[0]; //first and only one who matches this id

        //get transcripts
        var transcripts = sql("SELECT * FROM Transcripts WHERE gene_GeneID_id = ?", [finalAns.genes[i].gene_GeneID_id]);
        finalAns.genes[i].transcripts = transcripts;

        //get exons
        var geneExons = sql("SELECT  genomic_start_tx, genomic_end_tx FROM Exons WHERE gene_GeneID_id = ?", [finalAns.genes[i].gene_GeneID_id]);
        finalAns.genes[i].geneExons = geneExons;

        await Promise.all(finalAns.genes[i].transcripts.map(async (transcript, index) => {
            finalAns.genes[i].transcripts[index] = await findTranscriptInfo(transcript, useRepDomains)
        }))
    }
}

//get orthology
app.get('/getOrthologyGenes/:species/:gene', (req, res) => {
    console.log('Orthology');
    var gene = req.params.gene.toUpperCase();
    var species = req.params.species;
    var finalResults=[];

    //search by name only
    var similarGenes= sql("SELECT gene_symbol,specie FROM Genes WHERE (UPPER( gene_ensembl_id ) = ? or UPPER( gene_symbol ) =? )", [gene, gene]);

    //check A
    var results = sql("SELECT * FROM Orthology WHERE (UPPER( A_ensembl_id ) = ? or UPPER( A_GeneSymb ) =? ) AND A_Species = ?", [gene, gene, species]);
    finalResults=finalResults.concat(results);

    //check B
    results = sql("SELECT * FROM Orthology WHERE (UPPER( B_ensembl_id ) = ? or UPPER( B_GeneSymb ) =? ) AND B_Species = ?", [gene, gene, species]);
    finalResults=finalResults.concat(results);

    //check by matches in gene table
    results = closeGenes(gene);
    if (results.length > 0) {
        var found = undefined;
        for (var i = 0; i < results.length; i++) {
            if (results[i].specie == species) {
                found = results[i];
            }
        }
        if (found != undefined) {
            gene=found.gene_symbol.toUpperCase();
            console.log(gene);
            //check A
            results = sql("SELECT * FROM Orthology WHERE (UPPER( A_ensembl_id ) = ? or UPPER( A_GeneSymb ) =? ) AND A_Species = ?", [gene, gene, species]);
            finalResults=finalResults.concat(results);
 
            //check B
            results = sql("SELECT * FROM Orthology WHERE (UPPER( B_ensembl_id ) = ? or UPPER( B_GeneSymb ) =? ) AND B_Species = ?", [gene, gene, species]);
            finalResults=finalResults.concat(results);

            if (finalResults.length > 0) {
                res.status(200).send([finalResults,similarGenes]);
                return;
            }

            res.status(200).send([]);
            return;
        }
    }

    if (finalResults.length > 0 || similarGenes.length > 0 ) {
        res.status(200).send([finalResults,similarGenes]);
        return;
    }

    res.status(200).send([]);
});

module.exports = app;