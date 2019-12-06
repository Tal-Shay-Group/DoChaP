/*
this file was created to suite our needs for gene graphics. since the db only serves us with raw data.
this file calculates and decides what to forward to the website and the graphic works. this can be thought
as an controller or as an adapter. only 'createGraphicInfoForGene' function will be used but it will call the
other functions as needed.

*/

//This will receive the gene and create another gene object which can be used by the result controller for further use.
function createGraphicInfoForGene(gene) {
    var ansGene = new Object();
    ansGene.transcripts = [];
    ansGene.gene_symbol = gene.gene.gene_symbol; 
    ansGene.gene_id = gene.gene.gene_id;
    ansGene.strand= gene.gene.strand; 
    ansGene.synonyms=gene.gene.synonyms;
    ansGene.chromosome=gene.gene.chromosome;
    ansGene.description=gene.gene.description; 
    ansGene.MGI_id=gene.gene.MGI_id; 
    
    //var geneColorRand1=Math.floor(Math.random() * 16); currently not in use
    var geneExons=createGeneExonInfo(gene.geneExons);
    //calculate things for each transcript
    var start = findStartCoordinate(gene.transcripts);
    var end = findEndCoordinate(gene.transcripts);
    var maxProteinLength= findmaxProteinLength(gene.transcripts);
    for (var i = 0; i < gene.transcripts.length; i++) {
        ansGene.transcripts[i] = createGraphicInfoForTranscript(gene.transcripts[i], start, end,maxProteinLength, geneExons);
    } 
    //for showing nm before xm
    function compare( a, b ) {
        if ( a.id < b.id ){
          return -1;
        }
        if ( a.id > b.id ){
          return 1;
        }
        return 0;
      }
      ansGene.transcripts.sort(compare);
    ansGene.scale=createScale(start,end,gene.gene.strand);

    return ansGene;
}
function createScale(start,end,strand){
    var scale=new Object;
    scale.length=end-start;
    scale.strand=strand;
    return scale;
}

/* this function is a helper function that will focus on each transcript info and calculations.
we have function to calculate start and end as described individually
*/
function createGraphicInfoForTranscript(transcript, startCoordinate, endCoordinate,maxProteinLength, geneExons) {
    var ansTranscript = new Object();
    ansTranscript.id = transcript.transcript_id;
    ansTranscript.proteinId = transcript.protein.protein_id;
    ansTranscript.proteinLength = transcript.protein.length * 3 ;// in base units
    ansTranscript.exons = [];
    ansTranscript.length = endCoordinate - startCoordinate;
    ansTranscript.maxProteinLength=maxProteinLength;
    var cdsStart=transcript.cds_start;
    var cdsEnd=transcript.cds_end;

    //calculate things for each transcript
    for (var i = 0; i < transcript.transcriptExons.length; i++) {
        ansTranscript.exons[i] = new Object();
        ansTranscript.exons[i].transcriptViewStart = transcript.transcriptExons[i].genomic_start_tx - startCoordinate;
        ansTranscript.exons[i].transcriptViewEnd = transcript.transcriptExons[i].genomic_end_tx - startCoordinate;
        ansTranscript.exons[i].exonViewStart = transcript.transcriptExons[i].abs_start_CDS;
        ansTranscript.exons[i].exonViewEnd = transcript.transcriptExons[i].abs_end_CDS;
        ansTranscript.exons[i].name =""// getGeneExonName(geneExons,transcript.transcriptExons[i].genomic_start,transcript.transcriptExons[i].genomic_end);
        ansTranscript.exons[i].id = transcript.transcriptExons[i].abs_end;
        ansTranscript.exons[i].color = geneExons[transcript.transcriptExons[i].genomic_start_tx][transcript.transcriptExons[i].genomic_end_tx].color;
        ansTranscript.exons[i].isUTRStart=undefined;
        ansTranscript.exons[i].isUTREnd=undefined;
        ansTranscript.exons[i].isUTRAll=false;
        
        
        if(transcript.transcriptExons[i].abs_start_CDS==0){ //that is the representation is the database
            ansTranscript.exons[i].isUTRAll=true;
        }
        else{
            if(transcript.transcriptExons[i].genomic_start_tx<=cdsStart && cdsStart <=transcript.transcriptExons[i].genomic_end_tx){
            //cds_start in mid exon
            ansTranscript.exons[i].isUTRStart=cdsStart-transcript.transcriptExons[i].genomic_start_tx;
        }
        if(transcript.transcriptExons[i].genomic_start_tx<=cdsEnd && cdsEnd <=transcript.transcriptExons[i].genomic_end_tx ){
            //cds_end in mid exon
            ansTranscript.exons[i].isUTREnd=cdsEnd-transcript.transcriptExons[i].genomic_start_tx;
        }
        } 
        
    }

    //get the domain info needed about this transcript
    let domains = transcript.domains;
    ansTranscript.domains = [];
    for (var i = 0; i < domains.length; i++) {
        ansTranscript.domains[i] = new Object();
        ansTranscript.domains[i].start = domains[i].nuc_start;
        ansTranscript.domains[i].end = domains[i].nuc_end;
        ansTranscript.domains[i].name = domains[i].domainType.name;
        ansTranscript.domains[i].typeID = domains[i].domainType.type_id;
        ansTranscript.domains[i].overlap=false;
    }
    findOverlaps(ansTranscript.domains);
    orderBySize(ansTranscript.domains);

    return ansTranscript;
}

//finds start coordinates by finding the 'earliest coordinate' mentioned from all transcripts of this gene
function findStartCoordinate(transcripts) {
    var minStartPoint = transcripts[0].tx_start; // implying there is at least one transcript . if there is infinity it would be better for init 
    for (var i = 0; i < transcripts.length; i++) {
        if (minStartPoint > transcripts[i].tx_start) {
            minStartPoint = transcripts[i].tx_start;
        }
    }
    return minStartPoint;
}

//finds end coordinates by finding the 'latest coordinate' mentioned from all transcripts of this gene
function findEndCoordinate(transcripts) {
    var endPoint = transcripts[0].tx_end; // implying there is at least one transcript . if there is infinity it would be better for init 
    for (var i = 0; i < transcripts.length; i++) {
        if (endPoint < transcripts[i].tx_end) {
            endPoint = transcripts[i].tx_end;
        }
    }
    return endPoint;
}

function findmaxProteinLength(transcripts){
    var maxProtein=0;
    for(var i=0; i<transcripts.length;i++){
        if( transcripts[i].protein.length>maxProtein){
            maxProtein=transcripts[i].protein.length;
        }
    }
    return maxProtein*3; //because we need length in nucleotides
}

function createGeneExonInfo(geneExons){
    var exonInfo={};
    var colorArr= ["#B627FC", "#BBABF3", "#DE3D3D", "#FF6262", "#f5b0cb", "#E8A089", "#FFDFD3","#ee9572", "#FD9900",
    "#deb881", "#e3b04b","#ffb90f","#ffd700", "#FFFC3B", "#FFF599", "#FFFED3", "#D3D6A5", "#ccff00", "#20F876", "#63C37F",
    "#A6AB75", "#A6B9B4", "#beebe9", "#00ccff", "#7BEAD2", "#180CF5", "#77624A"
];
    for( var i=0; i<geneExons.length;i++){
        if(exonInfo[geneExons[i].genomic_start_tx]==undefined){
            exonInfo[geneExons[i].genomic_start_tx]=[];
        }
        var chosenColor=getcolorFromList(colorArr);
        if(colorArr.length<2){
            colorArr= ["#B627FC", "#BBABF3", "#DE3D3D", "#FF6262", "#f5b0cb", "#E8A089", "#FFDFD3","#ee9572", "#FD9900",
            "#deb881", "#e3b04b","#ffb90f","#ffd700", "#FFFC3B", "#FFF599", "#FFFED3", "#D3D6A5", "#ccff00", "#20F876", "#63C37F",
            "#A6AB75", "#A6B9B4", "#beebe9", "#00ccff", "#7BEAD2", "#180CF5", "#77624A"
        ];
        }
        exonInfo[geneExons[i].genomic_start_tx][geneExons[i].genomic_end_tx]={color:chosenColor,name:""};
    }
    return exonInfo;
}

function findOverlaps(domains){
    function compare( a, b ) {
        if ( a.start < b.start ){
          return -1;
        }
        if ( a.start > b.start ){
          return 1;
        }
        if ( a.start == b.start && a.end < b.end){
            return 1;
          }
        return 0;
      }
      domains.sort(compare);
      for( var i=0; i<domains.length;i++){
          if(domains[i].overlap==true){ //already known to overlap
              continue;
          }
        for(var j=i+1;j<domains.length;j++){
            if(domains[i].end>=domains[j].start){ //overlap
                domains[i].overlap=true;
                domains[j].overlap=true;
            }
            else{
                break; //if we are not overlapping then further domains will not too;\
            }
        }
      }
}
function orderBySize(domainArr){
    function compare( a, b ) {
        aLength=a.end-a.start;
        bLength=b.end-b.start;
        if ( aLength > bLength ){
          return -1;
        }
        if ( aLength < bLength ){
          return 1;
        }
        return 0;
      }
      domainArr.sort(compare);
}