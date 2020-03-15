/**
 * this service can be accessed from every page. If needed to search for gene by text-field
 */
angular.module("DoChaP").service("querySearchService", function ($window,webService) {
    self = this;

    //in case of text this function runs. it checks for invalid input before sending it to the server
    self.queryHandler =async function (query, specie, isReviewed) {
        var re = new RegExp("^[a-zA-Z0-9]");
        query=query.trim(); //trim whitespaces from beginning or end
        if (!re.test(query)) {
            return ["error", "Please fix your query"];
        }
        return await webService.queryHandler(query, specie, isReviewed)
            .then(function (response) {
                var geneList = response.data.genes[0];
                if (geneList==undefined || geneList.transcripts.length == 0) {
                    return ["error", "No results were found"];
                } else {
                    if (response.data.isExact == true || response.data.genes.length == 1) {
                        $window.sessionStorage.setItem("currGene", JSON.stringify(response.data));
                        $window.sessionStorage.setItem("ignorePredictions", "false");
                        $window.location = "#!/results";
                        return ["success"];
                    } else {
                        message = "";
                        var messageForHomePage="";
                        for (var i = 0; i < response.data.genes.length - 1; i++) {
                            message = message + response.data.genes[i].gene_symbol + ", ";
                            messageForHomePage=messageForHomePage+
                            "<a ng-click=\"querySearchCtrl.exmaple('"+response.data.genes[i].gene_symbol+"')\">"+
                            response.data.genes[i].gene_symbol+"</a>"+", ";
                        }
                        message = "We couldn't find an exact match for your query. Did you mean:\n" +message + response.data.genes[response.data.genes.length - 1].gene_symbol;
                        messageForHomePage = "We couldn't find an exact match for your query. Did you mean:\n"+messageForHomePage  + "<a ng-click=\"querySearchCtrl.exmaple('"+response.data.genes[response.data.genes.length - 1].gene_symbol+"')\">"+response.data.genes[response.data.genes.length - 1].gene_symbol+"</a>";
                        return ["error", message,messageForHomePage];
                    }
                }
            })
            .catch(function (response) {
                if (response.data != undefined) {
                    return ["error", "Sorry! No results were found"];
                } else {
                    return ["error", "Error! We ran into a problem.\nIf you keep seeing this error you can contact us for help"];
                }
            });
            
}
})