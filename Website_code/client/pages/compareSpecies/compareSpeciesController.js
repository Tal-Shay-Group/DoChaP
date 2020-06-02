/*
 *
 * this is one of the most special pages in the site. 
 * we compare the same gene in different species so we need to manage two different yet similar genes
 * and sometimes anaylize together and sometimes alone.
 * 
 */

angular.module("DoChaP").controller('compareSpeciesController', function ($window, $scope, $route, compareSpeciesService, webService) {
  //init parameters
  self = this;
  $scope.loading = false;
  $scope.alert = "";
  $scope.genes = undefined;
  $scope.results = undefined;
  self.currSpecies = 0;
  $scope.canvasSize = $(window).width() / 5;
  self.toolTipManagerForCanvas = {};
  $scope.orthologyList = undefined;
  $scope.viewMode = "all";
  $scope.options = false;

  //when click on search
  self.geneSearch = async function () {
    $scope.loading = true;
    await compareSpeciesService.geneSearch(specie1ComboBox.value, compareGeneSearchTextField.value, specie2ComboBox.value, orthologyComboBox.value)
      .then(function (response) {
        $scope.loading = false;

        //if there is error
        if (response[0] == "error") {
          $scope.alert = response[1];
          $scope.$apply();

        } else {
          //success senario
          $scope.alert = "";
          self.specie1Gene = response[1][0];
          self.specie2Gene = response[1][1];
          $scope.shownTranscripts1 = self.specie1Gene.transcripts.length;
          $scope.hiddenTranscripts1 = 0;
          $scope.shownTranscripts2 = self.specie2Gene.transcripts.length;
          $scope.hiddenTranscripts2 = 0;
          self.createScales();

          //draw
          $(document).ready(function () {
            $scope.$apply();
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

  //updating all canvases,scales,tooltips
  function updateCanvases() {
    //drawing transcripts
    for (var i = 0; i < self.specie1Gene.transcripts.length; i++) {
      $('#fadeinDiv1' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
      self.specie1Gene.transcripts[i].show('canvas-genomic1' + i, 'canvas-transcript1' + i, 'canvas-protein1' + i, self.toolTipManagerForCanvas, 'canvas-protein-extend1' + i);
    }

    for (var i = 0; i < self.specie2Gene.transcripts.length; i++) {
      $('#fadeinDiv2' + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));
      self.specie2Gene.transcripts[i].show('canvas-genomic2' + i, 'canvas-transcript2' + i, 'canvas-protein2' + i, self.toolTipManagerForCanvas, 'canvas-protein-extend2' + i);

    }

    //drawing scales
    self.specie1Gene.scale.draw("canvas-scale1");
    self.specie1Gene.proteinScale.draw("canvas-scale-protein1");
    self.specie1Gene.proteinScale.drawBehind("proteinGridlines1");
    self.specie1Gene.scale.drawBehind("genomicGridlines1");

    self.specie2Gene.scale.draw("canvas-scale2");
    self.specie2Gene.proteinScale.draw("canvas-scale-protein2");
    self.specie2Gene.proteinScale.drawBehind("proteinGridlines2");
    self.specie2Gene.scale.drawBehind("genomicGridlines2");

    $('#canvas-scale1').hide().fadeIn(1000);
    $('#canvas-scale-protein1').hide().fadeIn(1000);
    $('#canvas-scale2').hide().fadeIn(1000);
    $('#canvas-scale-protein2').hide().fadeIn(1000);

    $scope.chromosomeLocation1 = "chr" + self.specie1Gene.chromosome + ":" + numberToTextWithCommas(self.specie1Gene.scale.start) + "-" + numberToTextWithCommas(self.specie1Gene.scale.end);
    $scope.chromosomeLocation2 = "chr" + self.specie2Gene.chromosome + ":" + numberToTextWithCommas(self.specie2Gene.scale.start) + "-" + numberToTextWithCommas(self.specie2Gene.scale.end);
    
    //click for extended protein view
    $("canvas")
      .click(function (event) {
        Domain.domainClick(self.toolTipManagerForCanvas, event);
        $scope.$apply();
      });
      //range sliders:
    $('#genomic_range1').data("ionRangeSlider").update({
      from: self.specie1Gene.scale.start,
      to: self.specie1Gene.scale.end,
    });
    $('#protein_range1').data("ionRangeSlider").update({
      from: self.specie1Gene.proteinScale.zoomInStart,
      to: self.specie1Gene.proteinScale.zoomInEnd,
    });
    $('#genomic_range2').data("ionRangeSlider").update({

      from: self.specie2Gene.scale.start,
      to: self.specie2Gene.scale.end,
    });
    $('#protein_range2').data("ionRangeSlider").update({
      from: self.specie2Gene.proteinScale.zoomInStart,
      to: self.specie2Gene.proteinScale.zoomInEnd,
    });

    $scope.$apply();
  }

  //focus on text-field
  $(document).ready(function () {
    document.getElementById("compareGeneSearchTextField").focus();
  });

  //opening window
  $scope.showWindow = undefined;
  $scope.openWindow = function (type, id, species) {
    //selecting right species
    if (species == 1) {
      self.currSpecies = self.specie1Gene;
    } else if (species == 2) {
      self.currSpecies = self.specie2Gene;
    }

    //selecting right type
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

    webService.userLog("open_window,"+type+"+"+self.currSpecies.transcripts[id].id);
  }

  //closing modal when clicking outside of modal
  $scope.closeModalFromBackground = function (event) {
    if (event.target.id == 'BlackBackground') {
      $scope.showWindow = false
    }
  }

  //changing mode display
  $scope.checkboxChecked = function () {
    var type = selectModeComboBox.value;
    if ($scope.viewMode == type) {
      return;
    }
    $scope.viewMode = type;
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
    webService.userLog("partial_view,"+type);
  }
  //change mode between reviewed and unreviewed
  $scope.filterUnreviewed = function () {
    //getting genes
    $window.sessionStorage.setItem("ignorePredictions", "" + isReviewedCheckBox.checked);
    var results = $window.sessionStorage.getItem("currCompareSpecies");
    var genes = results.split("*");
    results = {
      "isExact": true,
      "genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
    };

    //calculate new list
    var newResults = compareSpeciesService.filterUnreviewed(results, isReviewedCheckBox.checked);
    
    //update page accordingly
    self.specie1Gene = newResults[0];
    self.specie2Gene = newResults[1];
    selectModeComboBox.value = 'all'; //update canvas + all views
    $scope.viewMode = 'all';
    $(document).ready(function () {
      updateCanvases();
    });
    webService.userLog("filter_unreviewed,"+isReviewedCheckBox.checked);
  }

  //hiding one transcript
  $scope.hideTranscriptView = function (index, species) { 
    var specieToChange = undefined;
    if (species == 1) {
      specieToChange = self.specie1Gene;
    } else if (species == 2) {
      specieToChange = self.specie2Gene;
    }
    specieToChange.transcripts[index].genomicView = false;
    specieToChange.transcripts[index].transcriptView = false;
    specieToChange.transcripts[index].proteinView = false;
    webService.userLog("hide_transcript,"+specieToChange.transcripts[index].id);
    countShownTranscripts();
  };

  //using example buttons
  self.exmaple = function (input) {
    $('#compareGeneSearchTextField').val(input);

    $('#compareGeneSearchTextField').css("font-weight", "bold");
    setTimeout(function () {
      $('#compareGeneSearchTextField').css("font-weight", "");
    }, 500);

  }

  //for gridlines. looking for number of transcripts and updating gridlines accordingly
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
    webService.userLog("show_transcript,"+specieToChange.transcripts[index].id);
  };


  //searching in server for matches
  self.searchForOrthology = function () {
    compareSpeciesService.fillOrthologyCombox(specie1ComboBox.value, compareGeneSearchTextField.value)
      .then(function (response) {
        var results = response.data;
        if (results.length == 0) {
          //not found:
          $scope.alert = "No orthology genes were found. Try another gene.";
          $scope.orthologyList = undefined;
        } else {
          //found and now updating
          $scope.orthologyList = results;
          $scope.options = undefined;
          $('#orthologyComboBox').empty();
          $scope.alert = "";
        }
      });
  }

  self.fillOrthologyCombox = function () {
    //init attributes
    var options1 = [];
    var options2 = [];
    var ensemblMatch = $scope.orthologyList[0];
    var geneSymbolMatch = $scope.orthologyList[1];

    //looking for matches in A B rows of orthology table
    if (specie1ComboBox.value != specie2ComboBox.value) {
      for (var i = 0; i < ensemblMatch.length; i++) {
        if (ensemblMatch[i].A_Species == specie2ComboBox.value) {
          options1.push(ensemblMatch[i].A_GeneSymb);
        }
        if (ensemblMatch[i].B_Species == specie2ComboBox.value) {
          options1.push(ensemblMatch[i].B_GeneSymb);
        }
      }

      //looking for gene_symbol matches if exists
      for (var i = 0; i < geneSymbolMatch.length; i++) {
        if (geneSymbolMatch[i].specie == specie2ComboBox.value) {
          options2.push(geneSymbolMatch[i].gene_symbol);
        }
      }
    }

    //if no results than block search button
    if (options1.length + options2.length == 0) {
      $scope.options = false;
      $('#orthologyComboBox').empty();
      return;
    }

    $scope.options = true;
    $('#orthologyComboBox').empty();

    //adding ensembl compara options
    if (options1.length > 0) {
      options1.sort();
      var option1tags = $('#orthologyComboBox').append($('<optgroup label="Ensembl compara"></optgroup>'));

      $.each(options1, function (i, p) {
        option1tags.append($('<option></option>').val(p).html(p));
      });
    }

    //adding gene symbol options
    if (options2.length > 0) {
      options2.sort();
      var alreadyInOrthology = false;
      for (var i = 0; i < options1.length; i++) {
        if (options1[i].toUpperCase() == options2[0].toUpperCase()) {
          alreadyInOrthology = true;
        }
      }
      if (alreadyInOrthology) {
        return;
      }
      var option2tags = $('#orthologyComboBox').append($('<optgroup label="Only gene symbol match"></optgroup>'));
      $.each(options2, function (i, p) {
        option2tags.append($('<option></option>').val(p).html(p));
      });
    }


  }

  //initializing scale when first showing results
  self.createScales = function () {
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
        $(document).ready(function () {
          updateCanvases();
        });

      }

    });

  }

});