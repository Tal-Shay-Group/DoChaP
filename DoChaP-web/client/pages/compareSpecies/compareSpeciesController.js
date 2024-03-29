/*
 *
 * this is one of the most special pages in the site. 
 * we compare the same gene in different species so we need to manage two different yet similar genes
 * and sometimes anaylize together and sometimes alone.
 * 
 */

angular.module("DoChaP").controller('compareSpeciesController', function ($window, $scope, $route, compareSpeciesService, webService) {
	//init parameters
	$scope.specie1Display = new Display();
	$scope.specie2Display = new Display();
	self = this;
	$scope.loading = false;
	$scope.alert = "";
	$scope.genes = undefined;
	self.currSpecies = 0;
	$scope.canvasSize = $(window).width() / 5;
	self.toolTipManagerForCanvas = {};
	$scope.orthologyList = undefined;
	$scope.viewMode = "all";
	$scope.options = false;
	// $scope.speciesToCompareModel = "";
	$scope.selectedSpecies2 = '';
	$scope.modeModel = "all";

	//fill specie combobox
	Species.fillSpecieComboBox("specie1ComboBox");
	// Species.fillSpecieComboBox("specie2ComboBox");

	//when click on search
	self.geneSearch = async function () {
		$scope.loading = true;
		await compareSpeciesService.geneSearch(specie1ComboBox.value, compareGeneSearchTextField.value, $scope.selectedSpecies2, orthologyComboBox.value)
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

					$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
					$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);

					$scope.shownTranscripts1 = self.specie1Gene.transcripts.length;
					$scope.hiddenTranscripts1 = 0;
					$scope.shownTranscripts2 = self.specie2Gene.transcripts.length;
					$scope.hiddenTranscripts2 = 0;


					//create range slider from left to right / right to left
					self.createScales();

					//write string for chromosome text
					$scope.chromosomeLocation1 = "chr" + self.specie1Gene.chromosome + ":" + numberToTextWithCommas(self.specie1Gene.scale.start) + "-" + numberToTextWithCommas(self.specie1Gene.scale.end);
					$scope.chromosomeLocation2 = "chr" + self.specie2Gene.chromosome + ":" + numberToTextWithCommas(self.specie2Gene.scale.start) + "-" + numberToTextWithCommas(self.specie2Gene.scale.end);


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
		$scope.specie1Display.canvasUpdater.updateCanvas(self.specie1Gene, self.toolTipManagerForCanvas, "1", $scope);
		$scope.specie2Display.canvasUpdater.updateCanvas(self.specie2Gene, self.toolTipManagerForCanvas, "2", $scope);
	}

	//focus on text-field
	$(document).ready(function () {
		document.getElementById("compareGeneSearchTextField").focus();
	});


	//for modals, need type of window and id of the clicked object
	$scope.openWindow = function (type, id, species) {
		//selecting right species
		if (species == 1) {
			self.currSpecies = self.specie1Gene;
		} else if (species == 2) {
			self.currSpecies = self.specie2Gene;
		}

		self.currSpecies.currTranscript = self.currSpecies.transcripts[id];
		$scope.specie1Display.modal.openWindow(type, self.currSpecies.currTranscript);
	}

	//changing mode display
	$scope.checkboxChecked = function () {
		var type = selectModeComboBox.value;
		if ($scope.viewMode == type) {
			return;
		}
		$scope.viewMode = type;

		$scope.specie1Display.transcriptDisplayManager.changeViewMode(type);
		$scope.specie2Display.transcriptDisplayManager.changeViewMode(type);
		countShownTranscripts();
		updateCanvases();
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

		updateCanvases();
	}

	self.GetSpecieDisplayBySpecieIndex = function (specieIndex) {
		if (specieIndex == 1) {
			return $scope.specie1Display;
		} else if (specieIndex == 2) {
			return $scope.specie2Display;
		}
	}

	//hiding one transcript
	$scope.hideTranscriptView = function (index, species) {
		var display = self.GetSpecieDisplayBySpecieIndex(species);
		display.transcriptDisplayManager.hideTranscriptByIndex(index);
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
		var results1 = $scope.specie1Display.transcriptDisplayManager.countShownTranscripts();
		$scope.shownTranscripts1 = results1.shownTranscripts;
		$scope.hiddenTranscripts1 = results1.hiddenTranscripts;

		var results2 = $scope.specie2Display.transcriptDisplayManager.countShownTranscripts();
		$scope.shownTranscripts2 = results2.shownTranscripts;
		$scope.hiddenTranscripts2 = results2.hiddenTranscripts;


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
		var display = self.GetSpecieDisplayBySpecieIndex(species);
		display.transcriptDisplayManager.showTranscript(index, $scope.viewMode);
		countShownTranscripts();
		updateCanvases();
	};


	//searching in server for matches
	self.searchForOrthology = function () {
		$scope.selectedSpecies2 = '';
		$('#orthologyComboBox').value = '';
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

	$scope.fillOrthologyCombox = function () {
		var options1 = [];
		var options2 = [];
		var ensemblMatch = $scope.orthologyList[0];
		var geneSymbolMatch = $scope.orthologyList[1];

		//looking for matches in A B rows of orthology table
		if (specie1ComboBox.value != $scope.selectedSpecies2) {
			for (var i = 0; i < ensemblMatch.length; i++) {
				if (ensemblMatch[i].A_Species == $scope.selectedSpecies2) {
					options1 = options1.concat(ensemblMatch[i].A_GeneSymb.split(", "));
				}
				if (ensemblMatch[i].B_Species == $scope.selectedSpecies2) {
					options1 = options1.concat(ensemblMatch[i].B_GeneSymb.split(", "));
				}
			}

			//looking for gene_symbol matches if exists
			for (var i = 0; i < geneSymbolMatch.length; i++) {
				if (geneSymbolMatch[i].specie == $scope.selectedSpecies2) {
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
			var option1tags = $('#orthologyComboBox').append($('<optgroup label="Orthology by Ensembl compara"></optgroup>'));

			$.each(options1, function (i, p) {
				option1tags.append($('<option></option>').val(p).html(p));
			});
		}

		//adding gene symbol options
		if (options2.length > 0) {
			options2 = options2.filter(function (item, pos) {
				return options2.indexOf(item) == pos;
			})
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
			var option2tags = $('#orthologyComboBox').append($('<optgroup label="Match by gene symbol"></optgroup>'));
			$.each(options2, function (i, p) {
				option2tags.append($('<option></option>').val(p).html(p));
			});
		}
	}



	// self.fillOrthologyCombox = function () {
	// 	//init attributes
	// 	var options1 = [];
	// 	var options2 = [];
	// 	var ensemblMatch = $scope.orthologyList[0];
	// 	var geneSymbolMatch = $scope.orthologyList[1];
	//
	// 	//looking for matches in A B rows of orthology table
	// 	if (specie1ComboBox.value != specie2ComboBox.value) {
	// 		for (var i = 0; i < ensemblMatch.length; i++) {
	// 			if (ensemblMatch[i].A_Species == specie2ComboBox.value) {
	// 				options1 = options1.concat(ensemblMatch[i].A_GeneSymb.split(", "));
	// 			}
	// 			if (ensemblMatch[i].B_Species == specie2ComboBox.value) {
	// 				options1 = options1.concat(ensemblMatch[i].B_GeneSymb.split(", "));
	// 			}
	// 		}
	//
	// 		//looking for gene_symbol matches if exists
	// 		for (var i = 0; i < geneSymbolMatch.length; i++) {
	// 			if (geneSymbolMatch[i].specie == specie2ComboBox.value) {
	// 				options2.push(geneSymbolMatch[i].gene_symbol);
	// 			}
	// 		}
	// 	}
	//
	// 	//if no results than block search button
	// 	if (options1.length + options2.length == 0) {
	// 		$scope.options = false;
	// 		$('#orthologyComboBox').empty();
	// 		return;
	// 	}
	//
	// 	$scope.options = true;
	// 	$('#orthologyComboBox').empty();
	//
	//
	// 	//adding ensembl compara options
	// 	if (options1.length > 0) {
	// 		options1.sort();
	// 		var option1tags = $('#orthologyComboBox').append($('<optgroup label="Orthology by Ensembl compara"></optgroup>'));
	//
	// 		$.each(options1, function (i, p) {
	// 			option1tags.append($('<option></option>').val(p).html(p));
	// 		});
	// 	}
	//
	// 	//adding gene symbol options
	// 	if (options2.length > 0) {
	// 		options2 = options2.filter(function (item, pos) {
	// 			return options2.indexOf(item) == pos;
	// 		})
	// 		options2.sort();
	// 		var alreadyInOrthology = false;
	// 		for (var i = 0; i < options1.length; i++) {
	// 			if (options1[i].toUpperCase() == options2[0].toUpperCase()) {
	// 				alreadyInOrthology = true;
	// 			}
	// 		}
	// 		if (alreadyInOrthology) {
	// 			return;
	// 		}
	// 		var option2tags = $('#orthologyComboBox').append($('<optgroup label="Match by gene symbol"></optgroup>'));
	// 		$.each(options2, function (i, p) {
	// 			option2tags.append($('<option></option>').val(p).html(p));
	// 		});
	// 	}
	// }

	//initializing scale when first showing results
	self.createScales = function () {
		//for genomic slider to know the limits (needed when strand=='-')
		self.maximumRange1 = self.specie1Gene.end;
		self.minimumRange1 = self.specie1Gene.start;
		self.maximumRange2 = self.specie2Gene.end;
		self.minimumRange2 = self.specie2Gene.start;

		//for genomic slider to know the direction of numbers
		$scope.genomicClass1 = $scope.specie1Display.locationScopeChanger.getChangerClassForStrand(self.specie1Gene.strand);
		$scope.genomicClass2 = $scope.specie2Display.locationScopeChanger.getChangerClassForStrand(self.specie2Gene.strand);

		if ($('#genomic_range1').data("ionRangeSlider") != undefined) {
			$('#genomic_range1').data("ionRangeSlider").destroy();
			$('#protein_range1').data("ionRangeSlider").destroy();
			$('#genomic_range2').data("ionRangeSlider").destroy();
			$('#protein_range2').data("ionRangeSlider").destroy();
		}

		self.createGenomicRangeSliders();

		var onFinishProtein1 = function (data) {
			var results = $window.sessionStorage.getItem("currCompareSpecies");
			var genes = results.split("*");
			results = {
				"isExact": true,
				"genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
			};
			var colors = true;
			var genes = results.genes;
			self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(genes, self.specie1Gene.specie), isReviewedCheckBox.checked, colors, self.specie1Gene.start, self.specie1Gene.end, data.from, data.to);
			$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
			$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
			updateCanvases();
		}

		var onFinishProtein2 = function (data) {
			var results = $window.sessionStorage.getItem("currCompareSpecies");
			var genes = results.split("*");
			results = {
				"isExact": true,
				"genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
			};
			var colors = true;
			var genes = results.genes;
			self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(genes, self.specie2Gene.specie), isReviewedCheckBox.checked, colors, self.specie2Gene.start, self.specie2Gene.end, data.from, data.to);
			$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
			$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
			updateCanvases();
		}

		$scope.specie1Display.locationScopeChanger.updateProteinlocationScopeChanger(
			'#protein_range1', onFinishProtein1, self.specie1Gene.proteinScale.length);

		$scope.specie2Display.locationScopeChanger.updateProteinlocationScopeChanger(
			'#protein_range2', onFinishProtein2, self.specie2Gene.proteinScale.length);

		// put handles in the ends because there is unupdated data that may be saved from recent genes
		if (self.specie1Gene.strand === '+') {
			$('#genomic_range1').data("ionRangeSlider").update({
				from: self.specie1Gene.scale.start,
				to: self.specie1Gene.scale.end,
			});
		} else {
			$('#genomic_range1').data("ionRangeSlider").update({
				from: self.maximumRange1 - self.specie1Gene.scale.end,
				to: self.maximumRange1 - self.specie1Gene.scale.start
			});
		}

		if (self.specie2Gene.strand === '+') {
			$('#genomic_range2').data("ionRangeSlider").update({
				from: self.specie2Gene.scale.start,
				to: self.specie2Gene.scale.end,
			});
		} else {
			$('#genomic_range2').data("ionRangeSlider").update({
				from: self.maximumRange2 - self.specie2Gene.scale.end,
				to: self.maximumRange2 - self.specie2Gene.scale.start
			});
		}

		$('#protein_range1').data("ionRangeSlider").update({
			from: self.specie1Gene.proteinScale.zoomInStart,
			to: self.specie1Gene.proteinScale.zoomInEnd,
		});
		$('#protein_range2').data("ionRangeSlider").update({
			from: self.specie2Gene.proteinScale.zoomInStart,
			to: self.specie2Gene.proteinScale.zoomInEnd,
		});

	}

	self.createGenomicRangeSliders = function () {
		var getResultsFromSessionStorage = function () {
			var results = $window.sessionStorage.getItem("currCompareSpecies");
			var genes = results.split("*");
			results = {
				"isExact": true,
				"genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
			};
			return {
				genes: results.genes,
				colors: true
			}
		}

		var onFinishWhenStrandPositive1 = function (data) {
			var results = getResultsFromSessionStorage();
			self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie1Gene.specie), isReviewedCheckBox.checked, results.colors, data.from, data.to, self.specie1Gene.proteinStart, self.specie1Gene.proteinEnd);
			$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
			$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
			updateCanvases();
		}

		var onFinishWhenStrandNegative1 = function (data) {
			var results = getResultsFromSessionStorage();
			self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie1Gene.specie), isReviewedCheckBox.checked, results.colors, self.maximumRange1 - data.to, self.maximumRange1 - data.from, self.specie1Gene.proteinStart, self.specie1Gene.proteinEnd);
			$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
			$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
			updateCanvases();
		}

		var onFinishWhenStrandPositive2 = function (data) {
			var results = getResultsFromSessionStorage();
			self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie2Gene.specie), isReviewedCheckBox.checked, results.colors, data.from, data.to, self.specie2Gene.proteinStart, self.specie2Gene.proteinEnd);
			$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
			$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
			updateCanvases();
		}

		var onFinishWhenStrandNegative2 = function (data) {
			var results = getResultsFromSessionStorage();
			self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie2Gene.specie), isReviewedCheckBox.checked, results.colors, self.maximumRange2 - data.to, self.maximumRange2 - data.from, self.specie2Gene.proteinStart, self.specie2Gene.proteinEnd);
			$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
			$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
			updateCanvases();
		}

		$scope.specie1Display.locationScopeChanger.updateGenomiclocationScopeChanger(
			'#genomic_range1', self.specie1Gene.scale, self.specie1Gene.strand, onFinishWhenStrandPositive1, onFinishWhenStrandNegative1,
			self.maximumRange1, self.minimumRange1);
		$scope.specie2Display.locationScopeChanger.updateGenomiclocationScopeChanger(
			'#genomic_range2', self.specie2Gene.scale, self.specie2Gene.strand, onFinishWhenStrandPositive2, onFinishWhenStrandNegative2,
			self.maximumRange2, self.minimumRange2);
	}

	//zoom genomic via button, direction can be "In" or "Out", specie index 1 or 2
	$scope.onZoomButtonGenomicClick = function (direction, specieIndex) {
		let display = self.GetSpecieDisplayBySpecieIndex(specieIndex);
		let genomicScaleName = "#genomic_range" + specieIndex;
		var gene = specieIndex == 1 ? self.specie1Gene : self.specie2Gene;
		var onFinishGenomicPositive = undefined;
		var onFinishGenomicNegative = undefined;

		var getResultsFromSessionStorage = function () {
			var results = $window.sessionStorage.getItem("currCompareSpecies");
			var genes = results.split("*");
			results = {
				"isExact": true,
				"genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
			};
			return {
				genes: results.genes,
				colors: true
			}
		}

		if (specieIndex == 1) {
			onFinishGenomicPositive = function (data) {
				var results = getResultsFromSessionStorage();
				self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie1Gene.specie), isReviewedCheckBox.checked, results.colors, data.from, data.to, self.specie1Gene.proteinStart, self.specie1Gene.proteinEnd);
				$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
				$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			};
			onFinishGenomicNegative = function (data) {
				var results = getResultsFromSessionStorage();
				self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie1Gene.specie), isReviewedCheckBox.checked, results.colors, self.maximumRange1 - data.to, self.maximumRange1 - data.from, self.specie1Gene.proteinStart, self.specie1Gene.proteinEnd);
				$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
				$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			};
		} else {
			onFinishGenomicPositive = function (data) {
				var results = getResultsFromSessionStorage();
				self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie2Gene.specie), isReviewedCheckBox.checked, results.colors, data.from, data.to, self.specie2Gene.proteinStart, self.specie2Gene.proteinEnd);
				$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
				$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			};
			onFinishGenomicNegative = function (data) {
				var results = getResultsFromSessionStorage();
				self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie2Gene.specie), isReviewedCheckBox.checked, results.colors, self.maximumRange2 - data.to, self.maximumRange2 - data.from, self.specie2Gene.proteinStart, self.specie2Gene.proteinEnd);
				$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
				$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			};
		}

		display.locationScopeChanger.zoomGenomicWithButton(gene.strand, gene.scale, direction, onFinishGenomicPositive, onFinishGenomicNegative, genomicScaleName, gene);
	}

	$scope.onZoomButtonProteinClick = function (direction, specieIndex) {
		var proteinScaleName = "#protein_range" + specieIndex;
		var gene = specieIndex == 1 ? self.specie1Gene : self.specie2Gene;
		var OnFinishProtein = undefined;

		if (specieIndex == 1) {
			OnFinishProtein = function (data) {
				var results = $window.sessionStorage.getItem("currCompareSpecies");
				var genes = results.split("*");
				results = {
					"isExact": true,
					"genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
				};
				var colors = true;
				var genes = results.genes;
				self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(genes, self.specie1Gene.specie), isReviewedCheckBox.checked, colors, self.specie1Gene.start, self.specie1Gene.end, data.from, data.to);
				$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
				$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			}
		} else if (specieIndex == 2) {
			OnFinishProtein = function (data) {
				var results = $window.sessionStorage.getItem("currCompareSpecies");
				var genes = results.split("*");
				results = {
					"isExact": true,
					"genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
				};
				var colors = true;
				var genes = results.genes;
				self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(genes, self.specie2Gene.specie), isReviewedCheckBox.checked, colors, self.specie2Gene.start, self.specie2Gene.end, data.from, data.to);
				$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
				$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			}
		}

		let display = self.GetSpecieDisplayBySpecieIndex(specieIndex);
		display.locationScopeChanger.zoomProteinWithButton(gene.proteinScale, direction, OnFinishProtein, proteinScaleName)
	}

	$scope.onExonClick = function (proteinStart, proteinEnd, genomicStart, genomicEnd, specieIndex) {
		//prepare variables
		var results = $scope.getResultsFromSessionStorage();
		var onFinishGenomicPositive = undefined;
		var onFinishGenomicNegative = undefined;

		if (specieIndex == 1) {
			self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie1Gene.specie), isReviewedCheckBox.checked, results.colors, genomicStart, genomicEnd, proteinStart, proteinEnd);
			$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
			$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
			updateCanvases();

			//update scales
			$("#protein_range" + specieIndex).data("ionRangeSlider").update({
				from: proteinStart,
				to: proteinEnd
			});
			onFinishGenomicPositive = function (data) {
				var results = $scope.getResultsFromSessionStorage();
				self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie1Gene.specie), isReviewedCheckBox.checked, results.colors, data.from, data.to, self.specie1Gene.proteinStart, self.specie1Gene.proteinEnd);
				$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
				$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			};
			onFinishGenomicNegative = function (data) {
				var results = $scope.getResultsFromSessionStorage();
				self.specie1Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie1Gene.specie), isReviewedCheckBox.checked, results.colors, self.maximumRange1 - data.to, self.maximumRange1 - data.from, self.specie1Gene.proteinStart, self.specie1Gene.proteinEnd);
				$scope.specie1Display.transcriptDisplayManager.addTranscripts(self.specie1Gene.transcripts);
				$scope.specie1Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			};
			$scope.specie1Display.locationScopeChanger.moveToSelectedGenomicRange(self.specie1Gene.strand, "#genomic_range" + specieIndex, genomicStart, genomicEnd, onFinishGenomicPositive, onFinishGenomicNegative, self.specie1Gene)


		} else if (specieIndex == 2) {
			self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie2Gene.specie), isReviewedCheckBox.checked, results.colors, genomicStart, genomicEnd, proteinStart, proteinEnd);
			$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
			$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
			updateCanvases();

			//update scales
			$("#protein_range" + specieIndex).data("ionRangeSlider").update({
				from: proteinStart,
				to: proteinEnd
			});
			onFinishGenomicPositive = function (data) {
				var results = $scope.getResultsFromSessionStorage();
				self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie2Gene.specie), isReviewedCheckBox.checked, results.colors, data.from, data.to, self.specie2Gene.proteinStart, self.specie2Gene.proteinEnd);
				$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
				$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			};
			onFinishGenomicNegative = function (data) {
				var results = $scope.getResultsFromSessionStorage();
				self.specie2Gene = new Gene(compareSpeciesService.getGeneForSpecie(results.genes, self.specie2Gene.specie), isReviewedCheckBox.checked, results.colors, self.maximumRange2 - data.to, self.maximumRange2 - data.from, self.specie2Gene.proteinStart, self.specie2Gene.proteinEnd);
				$scope.specie2Display.transcriptDisplayManager.addTranscripts(self.specie2Gene.transcripts);
				$scope.specie2Display.transcriptDisplayManager.changeViewMode($scope.viewMode);
				updateCanvases();
			};
			$scope.specie2Display.locationScopeChanger.moveToSelectedGenomicRange(self.specie2Gene.strand, "#genomic_range" + specieIndex, genomicStart, genomicEnd, onFinishGenomicPositive, onFinishGenomicNegative, self.specie2Gene)
		}
	}

	$scope.getResultsFromSessionStorage = function () {
		var results = $window.sessionStorage.getItem("currCompareSpecies");
		var genes = results.split("*");
		results = {
			"isExact": true,
			"genes": [JSON.parse(genes[0]), JSON.parse(genes[1])]
		};
		return {
			genes: results.genes,
			colors: true
		}
	}
});