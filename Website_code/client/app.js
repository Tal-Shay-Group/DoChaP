let app = angular.module('DoChaP', ["ngRoute"])

// config routes
app.config(function ($routeProvider) {
    $routeProvider
        // homepage
        .when('/', {
            /*
            templateUrl: 'pages/home/home.html',
            controller: 'homeController as homeCtrl'*/
            templateUrl: 'pages/querySearch/querySearch.html',
            controller: 'querySearchController as querySearchCtrl'
        })
        .when('/results', {
            templateUrl: 'pages/results/results.html',
            controller: 'resultsController as resultsCtrl'
        })
        .when('/querySearch',{
            templateUrl: 'pages/querySearch/querySearch.html',
            controller: 'querySearchController as querySearchCtrl'
        })
        .when('/underConstruction',{
            templateUrl: 'pages/underConstruction/underConstruction.html',
            controller: 'underConstructionController as underConstructionCtrl'
        })
        .when('/documentation',{
            templateUrl: 'pages/documentation/documentation.html',
            controller: 'documentationController as documentationCtrl'
        })
        
        // other
        .otherwise({ redirectTo: '/' }); //todo should be '/' when the site has a homepage

});