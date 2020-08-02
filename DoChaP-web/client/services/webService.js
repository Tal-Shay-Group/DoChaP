
/**
 * this service sends requests to the server.
 */

angular.module("DoChaP").service("webService", function ($http,$window) {
    var urlAdress="http://localhost:3000"
    this.queryHandler =function (query,specie,isReviewed) {
        var req = {
            method: 'GET',
            url: urlAdress+'/querySearch/' + query+"/"+specie+"/"+isReviewed , 
        };
        return $http(req);
    }

    // this.userLog = function(msg){
    //     var sessionID=$window.sessionStorage.getItem("sessionID")
    //     if (sessionID==undefined){
    //         return this.getNewSessionID().then(function(response){
    //             $window.sessionStorage.setItem("sessionID",response.data)
    //             sessionID=response.data;
    //             var time=new Date().toLocaleString().replace(/\//g,'-')
    //             var req = {
    //                 method: 'GET',
    //                 url: urlAdress+'/userLog/' +msg+","+time+","+sessionID,    
    //             };
    //             return $http(req);
    //         })
    //     }else{
    //         var time=new Date().toLocaleString().replace(/\//g,'-')
    //         var req = {
    //             method: 'GET',
    //             url: urlAdress+'/userLog/' +msg+","+time+","+sessionID,    
    //         };
    //         return $http(req);
    //     }
       
    // }

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
