/**
 * this is one of the most special pages in the site. 
 * we compare the same gene in different species so we need to manage two different yet similar genes
 * and sometimes anaylize together and sometimes alone.
 * 
 */

angular.module("DoChaP").controller('compareSpeciesController', function ($window, $scope, $route, compareSpeciesService) {
  self = this;
  $scope.loading = false;
  $scope.alert = "";
  $scope.genes = undefined;
  $scope.results=undefined;
  self.currSpecies=0;
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
      })
      .catch(function (response) {
        console.log(response);
        $scope.loading = false;
        $scope.alert = "sorry! unexepected error.";
        $scope.$apply();
      });
  } 
 
  function updateCanvases() {
   
    for (var i = 0; i < self.specie1Gene.transcripts.length; i++) {
       $('#fadeinDiv1' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
      buildGenomicView('canvas-genomic1' + i, self.specie1Gene.transcripts[i]);
      buildTranscriptView('canvas-transcript1' + i, self.specie1Gene.transcripts[i]);
      buildProteinView('canvas-protein1' + i, self.specie1Gene.transcripts[i]);

    }
    buildScaleView("canvas-scale1", self.specie1Gene.scale);
    buildScaleViewForProtein("canvas-scale-protein1", self.specie1Gene.proteinScale);

    for (var i = 0; i < self.specie2Gene.transcripts.length; i++) {
      $('#fadeinDiv2' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
      buildGenomicView('canvas-genomic2' + i , self.specie2Gene.transcripts[i]);
      buildTranscriptView('canvas-transcript2' + i, self.specie2Gene.transcripts[i]);
      buildProteinView('canvas-protein2' + i , self.specie2Gene.transcripts[i]);
    }
    buildScaleView("canvas-scale2", self.specie2Gene.scale);
    buildScaleViewForProtein("canvas-scale-protein2", self.specie2Gene.proteinScale);
    $('#canvas-scale1').hide().fadeIn(1000);
    $('#canvas-scale-protein1').hide().fadeIn(1000);
    $('#canvas-scale2').hide().fadeIn(1000);
    $('#canvas-scale-protein2').hide().fadeIn(1000);
    $scope.chromosomeLocation1=self.specie1Gene.chromosome + ":" + numberToTextWithCommas(self.specie1Gene.scale.start) + "-" + numberToTextWithCommas(self.specie1Gene.scale.end);
    $scope.chromosomeLocation2=self.specie2Gene.chromosome + ":" + numberToTextWithCommas(self.specie2Gene.scale.start) + "-" + numberToTextWithCommas(self.specie2Gene.scale.end);
    $scope.$apply();
  }

  $(document).ready(function () {
    document.addEventListener("keypress", function (event) {
      if (event.code == "Enter") {
        self.geneSearch();
      }
    });
    document.getElementById("compareGeneSearchTextField").focus();
  });

  $scope.showWindow = undefined;
  $scope.openWindow = function (type, id,species) {
    if(species==1){
      self.currSpecies=self.specie1Gene;
    }
    else if(species==2){
      self.currSpecies=self.specie2Gene;
    }
      $scope.showWindow = type;
      if (type == "transcript") {
          self.currSpecies.currTranscript = self.currSpecies.transcripts[id];
          self.currSpecies.currTranscript.tx_start = numberToTextWithCommas(self.currSpecies.currTranscript.tx_start);
          self.currSpecies.currTranscript.tx_end = numberToTextWithCommas(self.currSpecies.currTranscript.tx_end);
          self.currSpecies.currTranscript.cds_start = numberToTextWithCommas(self.currSpecies.currTranscript.cds_start);
          self.currSpecies.currTranscript.cds_end = numberToTextWithCommas(self.currSpecies.currTranscript.cds_end);
      } else if (type == "protein") {
          self.currTranscript = self.currSpecies.transcripts[id];
      }
      $scope.closeModalFromBackground = function (event) {
        if (event.target.id == 'BlackBackground') {
            $scope.showWindow = false
        }
    }
  }
  $scope.viewMode="all";
  $scope.checkboxChecked = function () {
    var type = selectModeComboBox.value;
    if ($scope.viewMode == type) {
        return;
    }
    $scope.viewMode = type;
    //if (type == "all") {
      //  $scope.canvasSize = 550;
   // } else {
      //  $scope.canvasSize = 1000;
   // }
    $(document).ready(function () {
        updateCanvases();
    });
    for (var i = 0; i < self.specie1Gene.transcripts.length; i++) {
        if (type === "genomic") {
          self.specie1Gene.transcripts[i].genomicView = true;
          self.specie1Gene.transcripts[i].transcriptView = false;
          self.specie1Gene.transcripts[i].proteinView = false;
    
        } else if (type === "transcript") {
          self.specie1Gene.transcripts[i].genomicView = false;
          self.specie1Gene.transcripts[i].transcriptView = true;
          self.specie1Gene.transcripts[i].proteinView = false;
        } else if (type === "protein") {
          self.specie1Gene.transcripts[i].genomicView = false;
          self.specie1Gene.transcripts[i].transcriptView = false;
          self.specie1Gene.transcripts[i].proteinView = true;
        } else if (type === "all") {
          self.specie1Gene.transcripts[i].genomicView = true;
          self.specie1Gene.transcripts[i].transcriptView = true;
          self.specie1Gene.transcripts[i].proteinView = true;
        } else if (type === "transcript_protein") {
          self.specie1Gene.transcripts[i].genomicView = false;
          self.specie1Gene.transcripts[i].transcriptView = true;
          self.specie1Gene.transcripts[i].proteinView = true;
        }

    }
    for (var i = 0; i < self.specie2Gene.transcripts.length; i++) {
      if (type === "genomic") {
        self.specie2Gene.transcripts[i].genomicView = true;
        self.specie2Gene.transcripts[i].transcriptView = false;
        self.specie2Gene.transcripts[i].proteinView = false;
  
      } else if (type === "transcript") {
        self.specie2Gene.transcripts[i].genomicView = false;
        self.specie2Gene.transcripts[i].transcriptView = true;
        self.specie2Gene.transcripts[i].proteinView = false;
      } else if (type === "protein") {
        self.specie2Gene.transcripts[i].genomicView = false;
        self.specie2Gene.transcripts[i].transcriptView = false;
        self.specie2Gene.transcripts[i].proteinView = true;
      } else if (type === "all") {
        self.specie2Gene.transcripts[i].genomicView = true;
        self.specie2Gene.transcripts[i].transcriptView = true;
        self.specie2Gene.transcripts[i].proteinView = true;
      } else if (type === "transcript_protein") {
        self.specie2Gene.transcripts[i].genomicView = false;
        self.specie2Gene.transcripts[i].transcriptView = true;
        self.specie2Gene.transcripts[i].proteinView = true;
      }

  }
}
$scope.filterUnreviewed = function () {
  $window.sessionStorage.setItem("ignorePredictions", "" + isReviewedCheckBox.checked);
  var newResults=compareSpeciesService.filterUnreviewed(JSON.parse($window.sessionStorage.getItem("currCompareSpecies")), isReviewedCheckBox.checked);
  self.specie1Gene=newResults[0];
  self.specie2Gene=newResults[1];
  selectModeComboBox.value='all';//update canvas+all biews shown
  $scope.viewMode='all';
  $scope.$apply();
}

$scope.changeTranscriptView = function (index,species) { //hide transcript. change name later
  var specieToChange=undefined;
  if(species==1){
    specieToChange=self.specie1Gene;
  }
  else if(species==2){
    specieToChange=self.specie2Gene;
  }
  specieToChange.transcripts[index].genomicView = false;
  specieToChange.transcripts[index].transcriptView = false;
  specieToChange.transcripts[index].proteinView = false;

};
self.exmaple = function (input) {
  $('#compareGeneSearchTextField').val(input);

  $('#compareGeneSearchTextField').css("font-weight", "bold");
  setTimeout(function () {
      $('#compareGeneSearchTextField').css("font-weight", "");
  }, 500);

}

});