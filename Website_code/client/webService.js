
/**
 * this service sends requests to the server.
 */

angular.module("DoChaP").service("webService", function ($http, $window, $rootScope) {
    this.queryHandler =function (query,specie,isReviewed) {
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/querySearch/' + query+"/"+specie+"/"+isReviewed , 
        };
        return $http(req);
    }

    this.compareGenes = function(geneName){
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/querySearch/' + geneName+"/all/false",    
        };
        return $http(req);
    }
})
