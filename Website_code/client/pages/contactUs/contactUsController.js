

angular.module("DoChaP")
    .controller("contactUsController", function ($scope, $window, webService) {
        // button click count
        self = this;
        $scope.sendMail=function(){
            webService.sendMail(Uname.value,email.value,message.value); 
            $window.alert("Thank you "+Uname.value+". We will be in contact.")
        }
       
    });
