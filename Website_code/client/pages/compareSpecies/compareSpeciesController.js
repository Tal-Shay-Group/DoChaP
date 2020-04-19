/*
 *
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
  $scope.results = undefined;
  self.currSpecies = 0;
  $scope.canvasSize = $(window).width() / 5;
  self.toolTipManagerForCanvas = {};
  $scope.orthologyList = undefined;

  self.geneSearch = function () {
    $scope.loading = true;
    compareSpeciesService.geneSearch(specie1ComboBox.value, compareGeneSearchTextField.value, specie2ComboBox.value, orthologyComboBox.value)
      .then(function (response) {
        $scope.loading = false;
        if (response[0] == "error") {
          $scope.alert = response[1];

        } else {
          $scope.alert = "";
          $('#bg1').css("background-image", "none");
          $('#bg1').css("background-color", "white");
          // $('body').css("background-image", "none");

          self.specie1Gene = response[1][0];
          self.specie2Gene = response[1][1];

          $scope.shownTranscripts1 = self.specie1Gene.transcripts.length;
          $scope.hiddenTranscripts1 = 0;
          $scope.shownTranscripts2 = self.specie2Gene.transcripts.length;
          $scope.hiddenTranscripts2 = 0;


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
      self.specie1Gene.transcripts[i].show('canvas-genomic1' + i, 'canvas-transcript1' + i, 'canvas-protein1' + i, self.toolTipManagerForCanvas, 'canvas-protein-extend1' + i);
    }
    self.specie1Gene.scale.draw("canvas-scale1");
    self.specie1Gene.proteinScale.draw("canvas-scale-protein1");
    self.specie1Gene.proteinScale.drawBehind("proteinGridlines1");
    self.specie1Gene.scale.drawBehind("genomicGridlines1");

    for (var i = 0; i < self.specie2Gene.transcripts.length; i++) {
      $('#fadeinDiv2' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
      self.specie2Gene.transcripts[i].show('canvas-genomic2' + i, 'canvas-transcript2' + i, 'canvas-protein2' + i, self.toolTipManagerForCanvas, 'canvas-protein-extend2' + i);

    }
    self.specie2Gene.scale.draw("canvas-scale2");
    self.specie2Gene.proteinScale.draw("canvas-scale-protein2");
    self.specie2Gene.proteinScale.drawBehind("proteinGridlines2");
    self.specie2Gene.scale.drawBehind("genomicGridlines2");

    $('#canvas-scale1').hide().fadeIn(1000);
    $('#canvas-scale-protein1').hide().fadeIn(1000);
    $('#canvas-scale2').hide().fadeIn(1000);
    $('#canvas-scale-protein2').hide().fadeIn(1000);
    $scope.chromosomeLocation1 = self.specie1Gene.chromosome + ":" + numberToTextWithCommas(self.specie1Gene.scale.start) + "-" + numberToTextWithCommas(self.specie1Gene.scale.end);
    $scope.chromosomeLocation2 = self.specie2Gene.chromosome + ":" + numberToTextWithCommas(self.specie2Gene.scale.start) + "-" + numberToTextWithCommas(self.specie2Gene.scale.end);
    $("canvas")
      .click(function (event) {
        Domain.domainClick(self.toolTipManagerForCanvas, event);
        $scope.$apply();
      });
    if ($('#genomic_range1').data("ionRangeSlider") != undefined) {
      $('#genomic_range1').data("ionRangeSlider").destroy();
      $('#protein_range1').data("ionRangeSlider").destroy();
      $('#genomic_range2').data("ionRangeSlider").destroy();
      $('#protein_range2').data("ionRangeSlider").destroy();
    }

    $('#genomic_range1').ionRangeSlider({
      type: "double",
      min: self.specie1Gene.scale.start,
      max: self.specie1Gene.scale.end,
      from: self.specie1Gene.scale.start,
      to: self.specie1Gene.scale.end,
      drag_interval: true,
      skin: "square",
      onFinish: function (data) {
        var results = $window.sessionStorage.getItem("currCompareSpecies");
        var genes = results.split("*");
        results = {
          "isExact": true,
          "genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
        };
        var colors = getColorForLength(results, isReviewedCheckBox.checked);
        var genes = results.genes;
        self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(genes, self.specie1Gene.specie), isReviewedCheckBox.checked, colors, data.from, data.to, self.specie1Gene.proteinStart, self.specie1Gene.proteinEnd);
        $scope.transcripts = self.specie1Gene.transcripts;
        /*$scope.$apply();*/
        $(document).ready(function () {
          updateCanvases();
        });

      }

    });
    $('#genomic_range2').ionRangeSlider({
      type: "double",
      min: self.specie2Gene.scale.start,
      max: self.specie2Gene.scale.end,
      from: self.specie2Gene.scale.start,
      to: self.specie2Gene.scale.end,
      drag_interval: true,
      skin: "square",
      onFinish: function (data) {
        var results = $window.sessionStorage.getItem("currCompareSpecies");
        var genes = results.split("*");
        results = {
          "isExact": true,
          "genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
        };
        var colors = getColorForLength(results, isReviewedCheckBox.checked);
        var genes = results.genes;
        self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(genes, self.specie2Gene.specie), isReviewedCheckBox.checked, colors, data.from, data.to, self.specie2Gene.proteinStart, self.specie2Gene.proteinEnd);
        $scope.transcripts = self.specie2Gene.transcripts;
        /*$scope.$apply();*/
        $(document).ready(function () {
          updateCanvases();
        });

      }

    });
    $('#protein_range1').ionRangeSlider({
      type: "double",
      min: 0,
      max: self.specie1Gene.proteinScale.length,
      from: 0,
      to: self.specie1Gene.proteinScale.length,
      drag_interval: true,
      skin: "square",
      onFinish: function (data) {
        var results = $window.sessionStorage.getItem("currCompareSpecies");
        var genes = results.split("*");
        results = {
          "isExact": true,
          "genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
        };
        var colors = getColorForLength(results, isReviewedCheckBox.checked);
        var genes = results.genes;
        self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(genes, self.specie1Gene.specie), isReviewedCheckBox.checked, colors, self.specie1Gene.start, self.specie1Gene.end, data.from, data.to);
        $scope.transcripts = self.specie1Gene.transcripts;
        /*$scope.$apply();*/
        $(document).ready(function () {
          updateCanvases();
        });

      }

    });
    $('#protein_range2').ionRangeSlider({
      type: "double",
      min: 0,
      max: self.specie2Gene.proteinScale.length,
      from: 0,
      to: self.specie2Gene.proteinScale.length,
      drag_interval: true,
      skin: "square",
      onFinish: function (data) {
        var results = $window.sessionStorage.getItem("currCompareSpecies");
        var genes = results.split("*");
        results = {
          "isExact": true,
          "genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
        };
        var colors = getColorForLength(results, isReviewedCheckBox.checked);
        var genes = results.genes;
        self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(genes, self.specie2Gene.specie), isReviewedCheckBox.checked, colors, self.specie2Gene.start, self.specie2Gene.end, data.from, data.to);
        $scope.transcripts = self.specie2Gene.transcripts;
        /*$scope.$apply();*/
        $(document).ready(function () {
          updateCanvases();
        });

      }

    });






    $scope.$apply();
  }

  $(document).ready(function () {
    document.addEventListener("keypress", function (event) {
      try {
        if (event.code == "Enter") {
          self.geneSearch();
        }
      } catch (err) {}
    });
    document.getElementById("compareGeneSearchTextField").focus();
  });

  $scope.showWindow = undefined;
  $scope.openWindow = function (type, id, species) {
    if (species == 1) {
      self.currSpecies = self.specie1Gene;
    } else if (species == 2) {
      self.currSpecies = self.specie2Gene;
    }
    $scope.showWindow = type;
    if (type == "transcript") {
      self.currSpecies.currTranscript = self.currSpecies.transcripts[id];
      self.currSpecies.currTranscript.tx_start = numberToTextWithCommas(self.currSpecies.currTranscript.tx_start);
      self.currSpecies.currTranscript.tx_end = numberToTextWithCommas(self.currSpecies.currTranscript.tx_end);
      self.currSpecies.currTranscript.cds_start = numberToTextWithCommas(self.currSpecies.currTranscript.cds_start);
      self.currSpecies.currTranscript.cds_end = numberToTextWithCommas(self.currSpecies.currTranscript.cds_end);
    } else if (type == "protein") {
      self.currSpecies.currTranscript = self.currSpecies.transcripts[id];
    }
    $scope.closeModalFromBackground = function (event) {
      if (event.target.id == 'BlackBackground') {
        $scope.showWindow = false
      }
    }
  }
  $scope.viewMode = "all";
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
    var newResults = compareSpeciesService.filterUnreviewed(JSON.parse($window.sessionStorage.getItem("currCompareSpecies")), self.specie1Gene.specie, self.specie2Gene.specie, isReviewedCheckBox.checked);
    self.specie1Gene = newResults[0];
    self.specie2Gene = newResults[1];
    selectModeComboBox.value = 'all'; //update canvas+all biews shown
    $scope.viewMode = 'all';
    $(document).ready(function () {
      updateCanvases();
    });
  }

  $scope.hideTranscriptView = function (index, species) { //hide transcript. change name later
    var specieToChange = undefined;
    if (species == 1) {
      specieToChange = self.specie1Gene;
    } else if (species == 2) {
      specieToChange = self.specie2Gene;
    }
    specieToChange.transcripts[index].genomicView = false;
    specieToChange.transcripts[index].transcriptView = false;
    specieToChange.transcripts[index].proteinView = false;

    countShownTranscripts();

  };
  self.exmaple = function (input) {
    $('#compareGeneSearchTextField').val(input);

    $('#compareGeneSearchTextField').css("font-weight", "bold");
    setTimeout(function () {
      $('#compareGeneSearchTextField').css("font-weight", "");
    }, 500);

  }

  function countShownTranscripts() {
    var counter = 0;
    for (var i = 0; i < self.specie1Gene.transcripts.length; i++) {
      if (self.specie1Gene.transcripts[i].genomicView ||
        self.specie1Gene.transcripts[i].transcriptView ||
        self.specie1Gene.transcripts[i].proteinView) {
        counter = counter + 1;
      }
    }
    $scope.shownTranscripts1 = counter;
    $scope.hiddenTranscripts1 = self.specie1Gene.transcripts.length - counter;

    counter = 0;
    for (var i = 0; i < self.specie2Gene.transcripts.length; i++) {
      if (self.specie2Gene.transcripts[i].genomicView ||
        self.specie2Gene.transcripts[i].transcriptView ||
        self.specie2Gene.transcripts[i].proteinView) {
        counter = counter + 1;
      }
    }
    $scope.shownTranscripts2 = counter;
    $scope.hiddenTranscripts2 = self.specie2Gene.transcripts.length - counter;



    $(document).ready(function () {
      if ($scope.shownTranscripts1 > 0) {
        self.specie1Gene.scale.drawBehind("genomicGridlines1");
        self.specie1Gene.proteinScale.drawBehind("proteinGridlines1");
      }
      if ($scope.shownTranscripts2 > 0) {
        self.specie2Gene.scale.drawBehind("genomicGridlines2");
        self.specie2Gene.proteinScale.drawBehind("proteinGridlines2");
      }

    });

  }

  //show according to mode
  $scope.showTranscriptView = function (index, species) {
    var specieToChange = undefined;
    if (species == 1) {
      specieToChange = self.specie1Gene;
    } else if (species == 2) {
      specieToChange = self.specie2Gene;
    }
    var type = $scope.viewMode;
    if (type === "genomic") {
      specieToChange.transcripts[index].genomicView = true;
      specieToChange.transcripts[index].transcriptView = false;
      specieToChange.transcripts[index].proteinView = false;
    } else if (type === "transcript") {
      specieToChange.transcripts[index].genomicView = false;
      specieToChange.transcripts[index].transcriptView = true;
      specieToChange.transcripts[index].proteinView = false;
    } else if (type === "protein") {
      specieToChange.transcripts[index].genomicView = false;
      specieToChange.transcripts[index].transcriptView = false;
      specieToChange.transcripts[index].proteinView = true;
    } else if (type === "all") {
      specieToChange.transcripts[index].genomicView = true;
      specieToChange.transcripts[index].transcriptView = true;
      specieToChange.transcripts[index].proteinView = true;
    } else if (type === "transcript_protein") {
      specieToChange.transcripts[index].genomicView = false;
      specieToChange.transcripts[index].transcriptView = true;
      specieToChange.transcripts[index].proteinView = true;
    }

    countShownTranscripts();

  };

  self.searchForOrthology = function () {
    compareSpeciesService.fillOrthologyCombox(specie1ComboBox.value, compareGeneSearchTextField.value)
      .then(function (response) {
        var results = response.data;
        $scope.orthologyList = results;
        self.fillOrthologyCombox();
      });
  }
  self.fillOrthologyCombox = function () {
    var options = $scope.orthologyList[specie2ComboBox.value + "_name"].split("; ");
    $('#orthologyComboBox').empty();
    $.each(options, function (i, p) {
      $('#orthologyComboBox').append($('<option></option>').val(p).html(p));
    });
  }



});