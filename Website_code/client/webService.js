


angular.module("DoChaP").service("webService", function ($http, $window, $rootScope) {
    this.queryHandler = function (query,specie,isReviewed) {
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/querySearch/' + query+"/"+specie+"/"+isReviewed ,
            
        };
        return $http(req);


    }
    this.fileHandler = function () {

        var req = {
            method: 'GET',
            url: 'http://localhost:3000/fileSearch'

        }
        return $http(req)
    }
})
