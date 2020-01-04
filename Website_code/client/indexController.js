angular.module("DoChaP").controller('indexController', function ($scope, $location, querySearchService,$window,$route) {
   self = this;
   $scope.showQuickSearch = false;
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
      $scope.showQuickSearch = (currAddress != "#!querySearch" && currAddress != "#!compareSpecies" &&currAddress != "#!");
   });
   self.search = async function () {
      var query = indexTextField.value;
      var specie = indexSpecies.value;
      var isReviewed = true;
      if($scope.loading==true){
          return;
      }
      $scope.indexLoading = true;
      var results=await querySearchService.queryHandler(query, specie, isReviewed);
      $scope.indexLoading = false;
      $scope.$apply();
      if(results[0]=="error"){
          $window.alert(results[1]);
      }else{
         if ("#!" + $location.path().substring(1)=="#!results"){
            $route.reload();
         }
      }
  }


});