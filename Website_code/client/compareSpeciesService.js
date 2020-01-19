angular.module("DoChaP").service("compareSpeciesService", function ($window,webService) {
    this.specieTextInput="";
    //returns ["error","message"] or ["res",actualResult]
    this.geneSearch=function(textInput,specie1,specie2){
        if(specie1==specie2){
            return new Promise(function(resolve, reject) {
                  resolve(["error","choose different species"]);
              });
        }
        return webService.compareGenes(textInput)
        .then(function (response) {
            var genesFound = runGenesCreation(response.data,JSON.parse($window.sessionStorage.getItem("ignorePredictions")),{colorByLength:true});
            if (genesFound.length <=1) {
                return ["error","sorry! no results were found"];
            }
            /*else if(genesFound.length >=3){
                return ["error","sorry! found more genes than expected. try different name."];
            }*/
            else{
                var res=orderTheGenesBySpecie(genesFound,specie1,specie2);
                if(res==undefined){
                    return ["error","sorry! we could not find the gene in at least one of the species"];
                }
                $window.sessionStorage.setItem("currCompareSpecies",JSON.stringify(response.data));
                $window.sessionStorage.setItem("ignorePredictions", "false");
                return ["result",res];
            }
        })
        .catch(function (response) {
            if (response.data != undefined) {
                return ["error","sorry! no results were found"];
            } else {
                return ["error","sorry! we ran into a problem.\nIf you keep seeing this error you can contact us for help"];
            }
        });

    };
    function orderTheGenesBySpecie(genesFound,specie1,specie2){
        var specie1Gene=undefined;
        var specie2Gene=undefined;
        for(var i=0; i<genesFound.length;i++){
            if(genesFound[i].specie==specie1){
                specie1Gene=genesFound[i];
            }
            if(genesFound[i].specie==specie2){
                specie2Gene=genesFound[i];
            }
        } 
        if(specie1Gene==undefined || specie2Gene==undefined){
            return undefined;
        }
        return [specie1Gene,specie2Gene]
    }
    this.filterUnreviewed=function(results,ignorePredictions){
            return runGenesCreation(results,ignorePredictions,{colorByLength:true});       
    };
})