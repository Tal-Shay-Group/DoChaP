/**
 * this controller manages the top part of the site that stays there for everypage.
 * includes logo and navigation bar
 */
angular.module("DoChaP").controller('indexController', function ($scope, $location, querySearchService, $window, $route) {
   self = this;
   $scope.showQuickSearch = false;

   //changing text in page name to white if we are on the current page
   $scope.$on('$locationChangeSuccess', function () {
      var headers = $('li');
      var currAddress = "#!" + $location.path().substring(1);
      $('li a').each(function (i) {
         if ($(this).attr('href') == currAddress) {
            $(this).css("color", "white");
         } else {
            $(this).css("color", "rgb(170, 169, 169)");
         }
      });
      $scope.showQuickSearch = (currAddress != "#!querySearch" && currAddress != "#!compareSpecies" && currAddress != "#!");
   });

   //searching for query using the navigation text field
   self.search = async function () {
      $window.alert('1.5');
      var query = indexTextField.value;
      var specie = indexSpecies.value;
      var isReviewed = true;
      if ($scope.loading == true) {
         return;
      }
      $scope.indexLoading = true;
      var results = await querySearchService.queryHandler(query, specie, isReviewed);
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

   $(document).ready(function () {
      document.getElementById("indexTextField").addEventListener("keypress", function (event) {
         
         if (event.code == "Enter") {
            try{
               // $window.alert('1');
               // $window.alert(JSON.stringify(self));
               // $window.alert(JSON.stringify(self.search));
               self.search();
               // $window.alert('2');
            }
            catch(err){
            }
            
        }

      });
    });

});