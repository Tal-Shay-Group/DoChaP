/*
this controller is used by the search page and is used to collect input for the search.
*/

angular.module("DoChaP")
    .controller("querySearchController", function ($scope, $window, webService) {
        // button click count
        self = this;
        $scope.loading = false;
        $scope.alert="";


        //runs on 'analyze' button click. checks for input in text or file and sends the right request for the server.
        self.search = function () {
            var query = searchTextField.value;
            //var file = chooseButton.value;
            var specie = searchBySpecie.value;
            var isReviewed = true;//isReviewedCheckBox.checked;
            if (query != undefined) {
                self.queryHandler(query, specie, isReviewed);
                //} else if (file != undefined) {
                //    self.fileHandler(file);
            } else {
                $scope.alert="Fill One Of The Options";
                //window.alert('Fill One Of The Options');
            }
        }

        //in case of text this function runs. it checks for invalid input before sending it to the server
        self.queryHandler = function (query, specie, isReviewed) {
            var re = new RegExp("^[a-zA-Z0-9]");
            if (re.test(query) && $scope.loading == false) {
                $scope.loading = true;
                webService.queryHandler(query, specie, isReviewed)
                    .then(function (response) {
                        var geneList = response.data.genes[0];
                        if (geneList.transcripts.length == 0) {
                            $scope.loading = false;
                            if (response.data.isExact == true) {
                                $scope.alert="sorry! no reviewed results were found";
                                //$window.alert("sorry! no reviewed were results found");
                            } else {
                                $scope.alert="sorry! no results were found";
                                //$window.alert("sorry! no results were found");
                            }


                        } else {
                            if (response.data.isExact == true || response.data.genes.length==1) {
                                $window.sessionStorage.setItem("currGene", JSON.stringify(response.data));
                                $window.sessionStorage.setItem("ignorePredictions", "false");
                                $window.location = "#!/results";
                            } 
                            else {
                                $scope.loading = false;
                                message = "";
                                for (var i = 0; i < response.data.genes.length - 1; i++) {
                                    message = message + response.data.genes[i].gene_symbol + ", ";
                                }
                                message=message+response.data.genes[response.data.genes.length - 1].gene_symbol;
                                $scope.alert="we did not find exact results. you can try one of the following:\n"+message;
                                //$window.alert("we did not find exact results. you can try one of the following:\n"+message);
                            }

                        }

                    })
                    .catch(function (response) {
                        $scope.loading = false;
                        if (response.data != undefined) {
                            $scope.alert="sorry! no results were found";
                            //window.alert("sorry! no results found");
                        } else {
                            $scope.alert="error! we ran into a problem.\nIf you keep seeing this error you can contact us for help";
                            //window.alert("error! the server is off");
                        }
                    });

            } else if (!$scope.loading) {
                $scope.alert="please fix your query";
                //window.alert("Please Fix Your Query");
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
        $(document).ready(function () {
            document.getElementById("searchTextField").focus();
            document.addEventListener("keypress", function (event) {
                if (event.code == "Enter") {
                    self.search();
                }
            });

        });

        self.exmaple = function(input){
            $('#searchTextField').val(input);
        }

    });
