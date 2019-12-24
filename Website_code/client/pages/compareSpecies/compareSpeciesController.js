angular.module("DoChaP").controller('compareSpeciesController', function ($scope, webService, $window) {
  self = this;
  $scope.loading = false;
  $scope.alert = "";
  $scope.genes = undefined;
  self.humanGenes={};
  self.mouseGenes={};
  $scope.canvasSize=250;
  self.searchByGene = function () {
    if(specie2ComboBox.value==specie1ComboBox.value){
      $scope.alert = "choose different species";
      return;
    }
    $scope.loading = true;
    webService.compareGenes(compareGeneSearchTextField.value).then(function (response) {
        var geneList = runGenesCreation(response.data);
        $scope.loading = false;
        if (geneList.length <=1) {
          $scope.alert = "sorry! no results were found";
        } else {
          $scope.alert = "";
          $scope.genes = geneList;
          if(geneList[0].specie=='M_musculus'){
            self.mouseGenes=geneList[0];
            self.humanGenes=geneList[1];
          }
          else{
            self.mouseGenes=geneList[1];
            self.humanGenes=geneList[0];
          }
          $(document).ready(function(self) { 
            //closeLoadingText();
           // angular.element(document).ready(function(){
              //updateCanvases();
            //})
            updateCanvases();
        });
        }
      })
      .catch(function (response) {
        $scope.loading = false;
        if (response.data != undefined) {
          $scope.alert = "sorry! no results were found";
        } else {
          $scope.alert = "error! the server is off";
        }
      });
  }


  function updateCanvases(){
       
    for (var i=0; i<self.mouseGenes.transcripts.length;i++){
        buildGenomicView('canvas-genomic'+i, self.mouseGenes.transcripts[i]);
        buildTranscriptView('canvas-transcript'+i, self.mouseGenes.transcripts[i]);
        buildProteinView('canvas-protein'+i, self.mouseGenes.transcripts[i]);
     
    }
    buildScaleView("canvas-scale",self.mouseGenes.scale);
    buildScaleViewForProtein("canvas-scale-protein",self.mouseGenes.proteinScale);
    for (var i=0; i<self.humanGenes.transcripts.length;i++){
      buildGenomicView('canvas-genomic'+i+"H", self.humanGenes.transcripts[i]);
      buildTranscriptView('canvas-transcript'+i+"H", self.humanGenes.transcripts[i]);
      buildProteinView('canvas-protein'+i+"H", self.humanGenes.transcripts[i]);
    }
    buildScaleView("canvas-scaleH",self.humanGenes.scale);
    buildScaleViewForProtein("canvas-scale-proteinH",self.humanGenes.proteinScale);
}

$(document).ready(function () {
  document.addEventListener("keypress", function (event) {
      if (event.code == "Enter") {
          self.searchByGene();
      }
  });
  document.getElementById("compareGeneSearchTextField").focus();
});


});