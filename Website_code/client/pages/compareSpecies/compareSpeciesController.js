angular.module("DoChaP").controller('compareSpeciesController', function ($scope, compareSpeciesService) {
  self = this;
  $scope.loading = false;
  $scope.alert = "";
  $scope.genes = undefined;
  self.humanGenes = {};
  self.mouseGenes = {};
  $scope.canvasSize = 250;
  self.geneSearch = function () {
    $scope.loading = true;
    compareSpeciesService.geneSearch(compareGeneSearchTextField.value, specie1ComboBox.value, specie2ComboBox.value)
      .then(function (response) {
        $scope.loading = false;
        if (response[0] == "error") {
          $scope.alert = response[1];
        } else {
          $scope.alert = "";
          self.specie1Gene=response[1][0];
          self.specie2Gene=response[1][1];
          $(document).ready(function (self) {
            updateCanvases();
          });
        }
        $scope.$apply();
      })
      .catch(function (response) {
        console.log(response);
        $scope.loading = false;
        $scope.alert = "sorry! unexepected error.";
        $scope.$apply();
      });
  }
 /* self.searchByGene = function () {
    if (specie2ComboBox.value == specie1ComboBox.value) {
      $scope.alert = "choose different species";
      return;
    }
    $scope.loading = true;
    webService.compareGenes(compareGeneSearchTextField.value).then(function (response) {
        var geneList = runGenesCreation(response.data);
        $scope.loading = false;
        if (geneList.length <= 1) {
          $scope.alert = "sorry! no results were found";
        } else {
          $scope.alert = "";
          $scope.genes = geneList;
          if (geneList[0].specie == 'M_musculus') {
            self.mouseGenes = geneList[0];
            self.humanGenes = geneList[1];
          } else {
            self.mouseGenes = geneList[1];
            self.humanGenes = geneList[0];
          }
          $(document).ready(function (self) {
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

*/
  function updateCanvases() {

    for (var i = 0; i < self.specie1Gene.transcripts.length; i++) {
      buildGenomicView('canvas-genomic1' + i, self.specie1Gene.transcripts[i]);
      buildTranscriptView('canvas-transcript1' + i, self.specie1Gene.transcripts[i]);
      buildProteinView('canvas-protein1' + i, self.specie1Gene.transcripts[i]);

    }
    buildScaleView("canvas-scale1", self.specie1Gene.scale);
    buildScaleViewForProtein("canvas-scale-protein1", self.specie1Gene.proteinScale);

    for (var i = 0; i < self.specie2Gene.transcripts.length; i++) {
      buildGenomicView('canvas-genomic2' + i , self.specie2Gene.transcripts[i]);
      buildTranscriptView('canvas-transcript2' + i, self.specie2Gene.transcripts[i]);
      buildProteinView('canvas-protein2' + i , self.specie2Gene.transcripts[i]);
    }
    buildScaleView("canvas-scale2", self.specie2Gene.scale);
    buildScaleViewForProtein("canvas-scale-protein2", self.specie2Gene.proteinScale);
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