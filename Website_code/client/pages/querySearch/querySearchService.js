angular.module("DoChaP").service("querySearchService", function ($scope) {
    self = this;
    
        //runs on 'analyze' button click. checks for input in text or file and sends the right request for the server.
        self.search = function (searchTextFieldValue,searchBySpecieValue,isReviewedCheckBoxchecked) {
            var query = searchTextFieldValue;
            var specie = searchBySpecieValue;
            var isReviewed = isReviewedCheckBoxchecked;
            if (query != undefined) {
                self.queryHandler(query, specie, isReviewed);
                //} else if (file != undefined) {
                //    self.fileHandler(file);
            } else {
                $scope.alert="Fill One Of The Options";
                //window.alert('Fill One Of The Options');
            }
        }
})
