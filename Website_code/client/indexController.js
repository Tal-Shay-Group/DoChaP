
angular.module("DoChaP").controller('indexController', function ($scope,$location,$window) {
    self = this;
    $scope.showQuickSearch=false;
    $scope.$on('$locationChangeSuccess',function() { 
    var headers= $( 'li' );
    var currAddress="#!"+$location.path().substring(1);
    $('li a').each(function(i)
    {
       if($(this).attr('href')==currAddress){
          $(this).css("color", "white");
       }else{
        $(this).css("color", "rgb(170, 169, 169)");
       }
    });
    $scope.showQuickSearch=(currAddress!="#!querySearch" && currAddress!="#!");
 });


  }); 