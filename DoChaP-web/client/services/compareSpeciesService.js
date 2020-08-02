/**
 * this file contains the logic for search of species
 */

angular.module("DoChaP").service("compareSpeciesService", function ($window, webService) {
    this.specieTextInput = "";
    
    //search
    this.geneSearch =async function (specie1, gene1, specie2, gene2) {
        //input check
        if ( specie2== "" || gene2== "" || specie2=="? undefined:undefined ?" || gene2=="? undefined:undefined ?") {
           return ["error", "No orthology genes were found. Try another gene."];
        }
        
        //searching for both searches
        promiseGene1 = webService.queryHandler(gene1, specie1, false);
        promiseGene2 = webService.queryHandler(gene2, specie2, false);
        var genes=await Promise.all([promiseGene1, promiseGene2]);
        
        //errors
        if(promiseGene1==undefined || promiseGene2==undefined){
            return ["error", "sorry! we ran into a problem.\nIf you keep seeing this error you can contact us for help"];
        }
        if (genes[0].data.genes.length == 0 || genes[1].data.genes.length == 0) {
            return ["error", "sorry! no results were found"];
        } 
        
        //creating an object used for parsing
        foundGene1 = genes[0].data;
        foundGene2 = genes[1].data;
        var afterJoinGenes = {
            "isExact": true,
            "genes": [foundGene1.genes[0], foundGene2.genes[0]]
        };

        //creating return value
        var genesFound = runGenesCreation(afterJoinGenes, JSON.parse($window.sessionStorage.getItem("ignorePredictions")), {
            colorByLength: true
        });
        
        //error creating the return value
        if (genesFound.length <= 1) {
            return ["error", "sorry! no results were found"];
        } else {
        //returning it in two string connected in the middle with "*" for parsing reasons
            var a = JSON.stringify(foundGene1.genes[0]);
            var b = JSON.stringify(foundGene2.genes[0]);
            $window.sessionStorage.setItem("currCompareSpecies", a + "*" + b);
            $window.sessionStorage.setItem("ignorePredictions", "false");
            return ["result", genesFound];
        }
    }
 
    this.filterUnreviewed = function (results, ignorePredictions) {
        return runGenesCreation(results, ignorePredictions, {
            colorByLength: true
        });
    };

    //get the gene in the wanted specie
    this.getGeneForSpecie = function (genes, specie) {
        for (var i = 0; i < genes.length; i++) {
            if (genes[i].specie == specie) {
                return genes[i];
            }
        }
        return undefined;

    };

    this.fillOrthologyCombox = function (species, gene) {
        return webService.getOrthologyGenes(species, gene);
    }


});