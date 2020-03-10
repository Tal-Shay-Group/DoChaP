/**
 * configuring html pages for every page URL
 */
let app = angular.module('DoChaP', ["ngRoute"])

// config routes
app.config(function ($routeProvider) {
    $routeProvider
        // homepage
        .when('/', {
            /*
            templateUrl: 'pages/home/home.html',
            controller: 'homeController as homeCtrl'*/
            templateUrl: 'pages/home/querySearch.html',
            controller: 'querySearchController as querySearchCtrl'
        })
        .when('/results', {
            templateUrl: 'pages/results/results.html',
            controller: 'resultsController as resultsCtrl'
        })
        .when('/results/:specie/:query', {
            templateUrl: 'pages/results/results.html',
            controller: 'resultsController as resultsCtrl'
        })
        .when('/querySearch',{
            templateUrl: 'pages/home/querySearch.html',
            controller: 'querySearchController as querySearchCtrl'
        })
        .when('/underConstruction',{
            templateUrl: 'pages/underConstruction/underConstruction.html',
            controller: 'underConstructionController as underConstructionCtrl'
        })
        .when('/help',{
            templateUrl: 'pages/help/help.html',
            controller: 'helpController as helpCtrl'
        })
        .when('/contactUs',{
            templateUrl: 'pages/contactUs/contactUs.html',
            controller: 'contactUsController as contactUsCtrl'
        })
        .when('/compareSpecies',{
            templateUrl: 'pages/compareSpecies/compareSpecies.html',
            controller: 'compareSpeciesController as compareSpeciesCtrl'
        })
        .when('/about',{
            templateUrl: 'pages/about/about.html',
            controller: 'aboutController as aboutCtrl'
        })
        
        // other
        .otherwise({ redirectTo: '/' }); //todo should be '/' when the site has a homepage

});