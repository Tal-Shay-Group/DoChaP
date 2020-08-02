 async function similarityBetweenTranscripts() {
     var transcript1 = $('#search1Transcript1').val();
     var transcript2 = $('#search1Transcript2').val();
     var weights = parseWeights();

     comparison = new Comparison(await transcriptFromDatebase(transcript1), await transcriptFromDatebase(transcript2), new BetweenTranscriptsComparator(), new BetweenTranscriptsDrawer(), weights)
     comparison.search();
 }

 async function similarityBetweenGenesInSpecies() {
     var species = $('#search2Species').val();
     var gene = $('#search2Gene').val();
     var weights = parseWeights();

     gene = await geneFromDatebase(gene, species);
     comparison = new Comparison(gene, gene, new BetweenGenesInSpeciesComparator(), new BetweenGenesInSpeciesDrawer(), weights)
     comparison.search();
 }

 async function similarityBetweenGenes() {
     var gene = $('#search3Gene').val();
     var weights = parseWeights();

     gene = await allGenesFromDatebase(gene);
     comparison = new Comparison(gene, gene, new BetweenGenesComparator(), new BetweenGenesDrawer(), weights)
     comparison.search();
 }

 async function transcriptFromDatebase(transcript_id) {
     url = "https://dochap.bgu.ac.il/dochap/querySearch/";
     gene = await $.get(
         url + transcript_id + "/all/false", {},
         function (data) {
             return data;
         }
     );
     gene = gene.genes[0];
     transcript = undefined;
     for (var i = 0; i < gene.transcripts.length; i++) {
         if (gene.transcripts[i].transcript_refseq_id == transcript_id ||
             gene.transcripts[i].transcript_ensembl_id == transcript_id) {
             transcript = gene.transcripts[i];

         }
     }
     addName(transcript)
     return transcript;
 }
 async function geneFromDatebase(gene, species) {
     url = "https://dochap.bgu.ac.il/dochap/querySearch/";
     gene = await $.get(
         url + gene + "/" + species + "/true", {},
         function (data) {
             return data;
         }
     );
     for (var i = 0; i < gene.genes[0].transcripts.length; i++) {
         addName(gene.genes[0].transcripts[i]);
     }
     return gene.genes[0];
 }

 async function allGenesFromDatebase(gene) {
     url = "https://dochap.bgu.ac.il/dochap/querySearch/";
     gene = await $.get(
         url + gene + "/all/false", {},
         function (data) {
             return data;
         }
     );
     return gene.genes;
 }

 function parseWeights() {


     return [parseInt($('#weights1').val()),
         parseInt($('#weights2').val()),
         parseInt($('#weights3').val())
     ]
 }

 function addName(transcript) {
     ensemblName = transcript.transcript_ensembl_id;
     refseqName = transcript.transcript_refseq_id;
     if (ensemblName != undefined) {

         if (refseqName != undefined) {
             transcript.name = refseqName + "\n" + ensemblName;
         } else {
             transcript.name = ensemblName;
         }
     } else {
         transcript.name = refseqName;
     }
 }