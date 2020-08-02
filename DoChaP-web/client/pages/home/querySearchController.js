/*
this controller is used by the search page and is used to collect input for the search.
*/

angular.module("DoChaP")
    .controller("querySearchController", function ($scope,querySearchService, $compile) {
        self = this;
        $scope.loading = false;
        $scope.alert = "";

        //runs on 'analyze' button click. checks for input in text or file and sends the right request for the server.
        self.search = async function () {
            var query = searchTextField.value;
            var specie = searchBySpecie.value;
            var isReviewed = true;

            if($scope.loading==true){ //if we are already in a search
                return;
            }

            //start search
            $scope.loading = true;
            var results=await querySearchService.queryHandler(query, specie, isReviewed);
            $scope.loading = false;

            //parse results
            if(results[0]=="error"){
                if(results[2]!=undefined){ //got two or more matches (when searching for synonmys)
                    document.getElementById("alertText").innerHTML = results[2];
                    $compile($("#alertText").contents())($scope);
                    $scope.alert="";
                }
                else{ //error
                    $scope.alert=results[1];
                    $("#alertText").html("");
                }
                
            }
            $scope.$apply();
        }

        //when clicking on example button
        self.exmaple = function (input) {
            $('#searchTextField').val(input);
            if (input == "NM_001033537.2") {
                $('#searchBySpecie').val("M_musculus")
            }
            if (input == "NP_001230673.1") {
                $('#searchBySpecie').val("H_sapiens");
            }
            $('#searchTextField').css("font-weight", "bold");
            setTimeout(function () {
                $('#searchTextField').css("font-weight", "");
            }, 500);

        }

        $(document).ready(function () {
            //sliding boxes
            $(".greyArea").each( function( index, element ){
                $( this ).slideDown( 1000 );
                $( this ).show();
            });
            
            //focus on text-field
            document.getElementById("searchTextField").focus();
            
            //search on enter
            document.addEventListener("keypress", function (event) {
                if (event.code == "Enter") {
                    try{
                        self.search();
                    }
                    catch(err){

                    }
                    
                }
            });

        });


    });