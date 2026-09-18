/**
 * this controller manages the top part of the site that stays there for everypage.
 * includes logo and navigation bar
 */
angular.module("DoChaP").controller('indexController', function ($scope, $location, querySearchService, $window, $route,$rootScope) {
   self = this;
   $scope.showQuickSearch = false;

   //changing text in page name to white if we are on the current page
   $scope.$on('$locationChangeSuccess', function () {
      var headers = $('li');
      var currAddress = "#!" + $location.path().substring(1);
      $('li a').each(function (i) {
         if ($(this).attr('href') == currAddress) {
            $(this).css("color", "#52c0ff");
         } else {
            $(this).css("color", "white");
         }
      });
      $scope.showQuickSearch = (currAddress != "#!querySearch" && currAddress != "#!compareSpecies" && currAddress != "#!");
      //gene search (specie + gene text + button) doesn't apply on the DOMAS page - disable it there
      var onDomasPage = (currAddress == "#!domas");
      $('#indexSpecies, #indexTextField, #submitSearchButton').prop('disabled', onDomasPage);
   });

   //fill specie combobox
   Species.fillSpecieComboBox("indexSpecies");

   //The transcript view shows every domain type DoChaP holds, straight from
   //DomainEvent/DomainType - not the InterPro representative subset. The
   //checkbox that used to switch between them is gone; the value is kept
   //because search() still passes it to the query endpoint, where false is
   //also the server's own default.
   $scope.useRepDomains = false;

   //searching for query using the navigation text field
   $rootScope.search = async function () {
      var query = indexTextField.value;
      var specie = indexSpecies.value;
      var isReviewed = true;
      var useRepDomains = $scope.useRepDomains;
      if ($scope.loading == true) {
         return;
      }
      $scope.indexLoading = true;
      var results = await querySearchService.queryHandler(query, specie, isReviewed, useRepDomains);
      $scope.indexLoading = false;
      $scope.$apply();
      if (results[0] == "error") {
         $window.alert(results[1]);
      } else {
         if ("#!" + $location.path().substring(1) == "#!results") {
            $route.reload();
         }
      }
   }

});