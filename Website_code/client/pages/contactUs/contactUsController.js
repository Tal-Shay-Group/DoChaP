angular.module("DoChaP")
    .controller("contactUsController", function ($scope, $window, webService) {
        self = this;
        // when clicked on button to send
        $scope.sendMail=function(){
            webService.sendMail(Uname.value,email.value,message.value); 
            $window.alert("Thank you "+Uname.value+". We will be in contact.")
        }
       
    });
