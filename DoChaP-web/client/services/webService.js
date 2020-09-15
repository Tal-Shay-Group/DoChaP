
/**
 * this service sends requests to the server.
 */

angular.module("DoChaP").service("webService", function ($http,$window) {

    /**NOTICE: one urlAdress should be uncommented according to wanted use **/
    //for running locally uncomment this:
    var urlAdress="http://localhost:3000";

    //for running on server uncomment this:
    // var urlAdress="https://dochap.bgu.ac.il/dochap";


    this.queryHandler =function (query,specie,isReviewed) {
        var req = {
            method: 'GET',
            url: urlAdress+'/querySearch/' + query+"/"+specie+"/"+isReviewed , 
        };
        return $http(req);
    }

 
    this.sendMail = function(name,email,message){
        var req = {
            method: 'GET',
            url: urlAdress+'/sendMail/' +name+"/"+email+"/"+message,    
        };
        return $http(req);
    }

    this.getOrthologyGenes=function(species,gene){
        var req = {
            method: 'GET',
            url: urlAdress+'/getOrthologyGenes/' +species+"/"+gene,    
        };
        return $http(req);

    }

     this.getNewSessionID=function(){
        var req = {
            method: 'GET',
            url: urlAdress+'/getNewSessionID',    
        };
        return $http(req);
    }
})
