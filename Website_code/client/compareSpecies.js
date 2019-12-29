angular.module("DoChaP").service("compareSpeciesService", function ($http, $window, $rootScope,webService) {
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
            var genesFound = runGenesCreation(response.data,false,{colorByLength:true});
            if (genesFound.length <=1) {
                return ["error","sorry! no results were found"];
            }
            else if(genesFound.length >=3){
                return ["error","sorry! found more genes than expected. try different name."];
            }
            else{
                geneFound=orderTheGenesBySpecie(genesFound,specie1,specie2);
                return ["result",genesFound];
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
        if(genesFound[0].specie==specie1&&genesFound[1].specie==specie2){
            return genesFound;
        } else if (genesFound[1].specie==specie1&&genesFound[0].specie==specie2){
            return [genesFound[1],genesFound[0]]
        }
        else{
            //should never get here
            return undefined;
        }
    }

})