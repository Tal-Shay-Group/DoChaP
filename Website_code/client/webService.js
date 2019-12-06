


angular.module("DoChaP").service("webService", function ($http, $window, $rootScope) {
    this.queryHandler = function (query) {
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/querySearch/' + query ,
            
        };
        return $http(req);


    }
    this.fileHandler = function () {

        var req = {
            method: 'GET',
            url: 'http://localhost:3000/fileSearch'

        }
        return $http(req)




        //old functions
    }
    this.getQuestions = function () {

        var req = {
            method: 'GET',
            url: 'http://localhost:3000/view/getQuestions'

        }
        return $http(req)


    }
    this.search = function (search) {

        var req = {
            method: 'GET',
            url: 'http://localhost:3000/view/getAttractionsByName/' + search

        }
        return $http(req)
    }

    this.showAttraction = function (attractionName) {

        $window.location = "#!showAttraction";
        $window.sessionStorage.setItem("attraction", attractionName);
        //$window.alert(attractionName);

    }
    this.getAttractionsByCategory = function (categoryName) {
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/view/getAttractionsByCategory/' + categoryName

        }

        return $http(req)

    }

    this.currUser = function () {
        return $window.sessionStorage.getItem(username);

    }

    this.register = function (username, password, firstName, lastName, email, birthDate, city, country, qid1, qid2, ans1, ans2, categories) {
        var req = {
            method: 'POST',
            url: 'http://localhost:3000/private/register',
            data: JSON.stringify({
                "username": username,
                "password": password,
                "firstName": firstName,
                "lastName": lastName,
                "email": email,
                "birthDate": birthDate,
                "city": city,
                "country": country,
                "question1": qid1,
                "question2": qid2,
                "answer1": ans1,
                "answer2": ans2,
                "interests": categories
            }
            ),
            headers: { 'Content-Type': 'application/json' }
        };
        return $http(req);

    }


    this.getFavoriteAttractions = function () {
        var req = {
            method: 'GET',
            url: 'http://localhost:3000/view/getFavoriteAttractions',
            headers: {
                "x-auth-token":$window.sessionStorage.getItem("token")
            }
        }
        return $http(req);
    }

    this.updateMyAttractionSort = function () {
        var attractions = "";
        var rank = "";
        var currList = JSON.parse($window.sessionStorage.getItem("favorites"));
        if (currList.length >= 1) {
            attractions = currList[0].attractionName;
            rank = currList[0].rank;
            for (var i = 1; i < currList.length; i++) {
                attractions = attractions + ',' + currList[i].attractionName;
                rank = rank + ',' + currList[i].rank;
            }
        }
        var req = {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' , "x-auth-token":$window.sessionStorage.getItem("token") },
            url: 'http://localhost:3000/update/updateMyAttractionSort/' + attractions + '/' + rank
        }
        return $http(req);

    }
    this.isFavorite = function (attractionName) {
        var currList = JSON.parse($window.sessionStorage.getItem("favorites"));
        for (var i = 0; i < currList.length; i++) {
            if (currList[i] != undefined && currList[i].attractionName == attractionName) {
                return true;
            }

        }
        return false;
    }



    this.addFavorite = function (attractionName, picture) {
        var currList = JSON.parse($window.sessionStorage.getItem("favorites"));
        var size = currList.length;
        var newFavorite = new Object();
        newFavorite.attractionName = attractionName;
        newFavorite.rank = size + 1;
        newFavorite.picture = picture;
        currList.push(newFavorite);
        $window.sessionStorage.setItem("favorites", JSON.stringify(currList));
        $window.alert("attraction added");
        $rootScope.favoriteCount = currList.length;
    }
    this.removeFavorite = function (attractionName) {
        var currList = JSON.parse($window.sessionStorage.getItem("favorites"));
        var currRank = -1;
        for (var i = 0; i < currList.length; i++) {
            if (currList[i] != undefined && currList[i].attractionName == attractionName) {
                currRank = currList[i].rank;
                delete currList[i];
                break;
            }

        }
        var newCurrList = [];
        for (var i = 0; i < currList.length; i++) {
            if (currList[i] != undefined) {
                if (currList[i].rank > currRank) {
                    currList[i].rank = currList[i] - 1;
                    newCurrList.push(currList[i]);
                }
                else {
                    newCurrList.push(currList[i]);
                }
            }
        }
        $window.sessionStorage.setItem("favorites", JSON.stringify(newCurrList));
        $rootScope.favoriteCount = newCurrList.length;
    }

    this.getLastAttractions = function () {
        var req = {
            method: "GET",
            url: 'http://localhost:3000/view/getLastAttractions',
            headers: {
                "x-auth-token":$window.sessionStorage.getItem("token")
            }
        }
        return $http(req);
    }
    this.getRecommendedAttractions = function () {
        var req = {
            method: "GET",
            url: "http://localhost:3000/view/getMostPopularAttractionForUser",
            headers: {
                "x-auth-token":$window.sessionStorage.getItem("token")
            }
        }
        return $http(req);
    }
    this.getPopularAttractions = function () {
        var req = {
            method: "GET",
            url: 'http://localhost:3000/view/getRandomPopularAttractions'
        }
        return $http(req);
    }

    
    this.viewAttraction=function(attractionName){
        var req={
            method:"GET",
            url: 'http://localhost:3000/view/viewAttraction/' + self.attractionName
        }
        return $http(req);
    }

    this.getLastReviews=function(attractionName){
        var req={
            method:"GET",
            url: 'http://localhost:3000/view/getLastReviews/' + self.attractionName
        }
        return $http(req);
    }

    this.forgotPassword=function(username,question,answer){
        var req={
            method:"POST",
            url:'http://localhost:3000/private/forgotPassword',
            data: JSON.stringify({
                "username": username,
                "qid": question,
                "answer": answer 
            }),
            headers: { 'Content-Type': 'application/json' }
        }
        return $http(req);
    
    }

    this.addRating=function(rating,review,date,attractionName){
        var req={
            method:"POST",
            url:'http://localhost:3000/update/addRating',
            data: JSON.stringify({
                "token": $window.sessionStorage.getItem("token"),
                "rating": rating,
                "review": review,
                "date": date,
                "attractionName": attractionName 
            }),
            headers: { 'Content-Type': 'application/json', "x-auth-token":$window.sessionStorage.getItem("token") }
        }
        return $http(req);
    }
    
    this.getRatingToFavorites=function(favorites,i){
        var req={
            method:"GET",
            url: 'http://localhost:3000/view/viewAttraction/' + favorites[i].attractionName
        }
         $http(req).then(function mySuccess(response) {
            
 
            favorites[i].rating=response.data[0].rating;
      
          }, function myError(response) {
            $window.alert(response.data);
      
          });
      

    }
    this.getCategoryToFavorites=function(favorites,i){
        var req={
            method:"GET",
            url: 'http://localhost:3000/view/viewAttraction/' + favorites[i].attractionName
        }
         $http(req).then(function mySuccess(response) {
            

            favorites[i].category=response.data[0].category;
      
          }, function myError(response) {
            $window.alert(response.data);
      
          });
      

    }
})
