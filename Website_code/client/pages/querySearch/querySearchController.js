/*
this controller is used by the search page and is used to collect input for the search.
*/

angular.module("DoChaP")
    .controller("querySearchController", function ($scope, $window, webService) {
        // button click count
        self = this;
        $scope.loading=false;


        //runs on 'analyze' button click. checks for input in text or file and sends the right request for the server.
        self.search = function () {
            var query = searchTextField.value;
            //var file = chooseButton.value;

            if (query != undefined) {
                self.queryHandler(query);
            //} else if (file != undefined) {
            //    self.fileHandler(file);
            } else {
                window.alert('Fill One Of The Options');
            }
        }

        //in case of text this function runs. it checks for invalid input before sending it to the server
        self.queryHandler = function (query) {
            var re = new RegExp("^[a-zA-Z0-9]");
            if (re.test(query)) {
                webService.queryHandler(query)
                    .then(function (response) {
                        // window.alert(JSON.stringify(response));
                        $window.sessionStorage.setItem("currGene", JSON.stringify(response.data));
                        $window.location = "#!results";
                    })
                    .catch(function (response) {
                        $scope.loading=false;
                        if(response.data!=undefined){
                            window.alert("sorry! no results found");
                        }
                        else{
                            window.alert("error! the server is off");
                        }
                    });
                    $scope.loading=true;
            } else {
                window.alert("Please Fix Your Query");
            }
        }

        //runs on file selected. notice that its not yet written and only checks that the file exists.
        self.fileHandler = function (file) {
            if (file.exists) {
                webService.fileHandler(file);
            } else {
                window.alert("Please Choose a Valid File");
            }
        }
        $(document).ready(function() { 
            document.getElementById("searchTextField").focus();
            document.addEventListener("keypress", function(event){
                if(event.code=="Enter"){
                    self.search();
                }
            }
        );
        });
        
    });