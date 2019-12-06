/* we didnt yet work on the homepage so its empty  */
angular.module("DoChaP").controller('homeController', function ($scope, $http, webService, $window) {
  self = this;
/*
  if($window.sessionStorage.getItem("username") != "guest"){

  
  webService.getLastAttractions()
    .then(function mySuccess(response) {
      self.lastSaved = response.data;
      self.calculated= JSON.parse($window.sessionStorage.getItem("favorites"));
      self.lastSaved=[];
        for (var i = 0; i < Math.min(self.calculated.length,2); i++) {

          self.lastSaved[i]=self.calculated[self.calculated.length-1-i];
          
          self.lastSaved[i].isFavorite = webService.isFavorite(self.lastSaved[i].attractionName);
        }
  
     
    }, function myError(response) {
      self.lastSaved = response.statusText;

    });

  webService.getRecommendedAttractions()
    .then(function mySuccess(response) {
      self.recommended = response.data;
     

        for (var i = 0; i < self.recommended.length; i++) {
          self.recommended[i].isFavorite = webService.isFavorite(self.recommended[i].attractionName);
        }
     
    }, function myError(response) {
      self.recommended = response.statusText;

    });
}
  webService.getPopularAttractions()
    .then(function mySuccess(response) {
      self.popular = response.data;


    }, function myError(response) {
      self.popular = response.statusText;

    });

  self.webService = webService;
  
  self.addFavorite = function (attractionName, picture) {
    webService.addFavorite(attractionName, picture);
    for (var i = 0; i < self.lastSaved.length; i++) {
      if (self.lastSaved[i].attractionName == attractionName) {
        self.lastSaved[i].isFavorite = true;
      }
    }
    for (var i = 0; i < self.recommended.length; i++) {
      if (self.recommended[i].attractionName == attractionName) {
        self.recommended[i].isFavorite = true;
      }
    }
  }

  self.removeFavorite = function (attractionName) {
    webService.removeFavorite(attractionName);
    for (var i = 0; i < self.lastSaved.length; i++) {
      if (self.lastSaved[i].attractionName == attractionName) {
        self.lastSaved[i].isFavorite = false;
      }
    }
    for (var i = 0; i < self.recommended.length; i++) {
      if (self.recommended[i].attractionName == attractionName) {
        self.recommended[i].isFavorite = false;
      }
    }

  }*/
}); 
