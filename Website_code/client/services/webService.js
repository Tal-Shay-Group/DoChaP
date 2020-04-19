
/**
 * this service sends requests to the server.
 */

angular.module("DoChaP").service("webService", function ($http) {
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

    this.userLog = function(msg){
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/userLog/' +msg,    
        };
        return $http(req);
    }

    this.sendMail = function(name,email,message){
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/sendMail/' +name+"/"+email+"/"+message,    
        };
        return $http(req);
    }

    this.getOrthologyGenes=function(species,gene){
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/getOrthologyGenes/' +species+"/"+gene,    
        };
        return $http(req);

    }
})
