/*
this file was created to suite our needs for gene graphics. since the db only serves us with raw data.
this file calculates and decides what to forward to the website and the graphic works. this can be thought
as an controller or as an adapter. only 'createGraphicInfoForGene' function will be used but it will call the
other functions as needed.

*/
function runGenesCreation(result,ignorePredictions,preferences){
    var geneList=[];
    for(var i=0; i<result.genes.length;i++){
        geneList.push(createGraphicInfoForGene(result.genes[i],ignorePredictions,preferences));
    }
    return geneList;
}

//This will receive the gene and create another gene object which can be used by the result controller for further use.
function createGraphicInfoForGene(gene,ignorePredictionsT,preferences) {
    var ansGene = new Object();
    ansGene.transcripts = [];
    ansGene.gene_symbol = gene.gene_symbol; 
    ansGene.gene_id = gene.gene_id;
    ansGene.strand= gene.strand; 
    ansGene.synonyms=gene.synonyms;
    ansGene.chromosome=gene.chromosome;
    ansGene.description=gene.description; 
    ansGene.MGI_id=gene.MGI_id; 
    ansGene.ensembl_id=gene.ensembl_id; 
    ansGene.specie=gene.specie;
    ansGene.specieName=getSpecieName(gene.specie);
    ansGene.EnsemblLink=getEnsemblGeneLink(gene.ensembl_id,gene.specie); 
    /*if(ansGene.specie=="H_sapiens"){
        ansGene.specie="Human";
    }
    else if(ansGene.specie=="M_musculus"){
        ansGene.specie="Mouse";
    }
    */
    colorStyleByLength=false;
    if(preferences!=undefined && preferences.colorByLength!=undefined){
        colorStyleByLength=true;
    }
    ansGene.geneExons=createGeneExonInfo(gene.geneExons,gene.transcripts,ansGene,colorStyleByLength);
    
    //add preferences
    if(preferences!=undefined && preferences.start!=undefined){
        var start = preferences.start;    
    }
    else{
        var start = findStartCoordinate(gene.transcripts);
    }
    if(preferences!=undefined && preferences.end!=undefined){
        var end = preferences.end;    
    }
    else{
        var end = findEndCoordinate(gene.transcripts);
    }
    var maxProteinLength= findmaxProteinLength(gene.transcripts);
    if(preferences!=undefined && preferences.proteinStart!=undefined){
        var proteinStart = preferences.proteinStart;    
    }
    else{
        var proteinStart = 0;
    }
    if(preferences!=undefined && preferences.proteinEnd!=undefined){
        var proteinEnd = preferences.proteinEnd;    
    }
    else{
        var proteinEnd = maxProteinLength;
    }
    
    //push transcripts
    for (var i = 0; i < gene.transcripts.length; i++) {
        if(ignorePredictionsT==false || gene.transcripts[i].transcript_id.substring(0,2)=="NM"){
            ansGene.transcripts.push(createGraphicInfoForTranscript(gene.transcripts[i], start, end,maxProteinLength, ansGene.geneExons,ansGene.specie,proteinStart,proteinEnd));
       }
    } 
    //for showing by size (commented is showing nm before xm)
    function compare( a, b ) {
        /*if ( a.id.substring(0,2) < b.id.substring(0,2) ){
          return -1;
        }
        if ( a.id.substring(0,2) > b.id.substring(0,2) ){
          return 1;
        }*/
        if(a.proteinLength<b.proteinLength){
            return 1;
        }
        if(a.proteinLength>b.proteinLength){
            return -1;
        }
        return 0;
      }
    ansGene.transcripts=ansGene.transcripts.sort(compare);
    ansGene.scale=createScale(start,end,gene.strand,gene.chromosome);
    ansGene.proteinScale=createProteinScale(maxProteinLength);
   
    return ansGene;
}

//creating genomic scale object
function createScale(start,end,strand,chromosomeName){
    var scale=new Object;
    scale.start=start;
    scale.end=end;
    scale.strand=strand;
    scale.chromosomeName=chromosomeName;
    return scale;
}

//creating protein scale object
function createProteinScale(length){
    var proteinScale=new Object;
    proteinScale.length=length;
    return proteinScale;
}

/* this function is a helper function that will focus on each transcript info and calculations.
we have function to calculate start and end as described individually
*/
function createGraphicInfoForTranscript(transcript, startCoordinate, endCoordinate,maxProteinLength, geneExons,specie,proteinStart,proteinEnd) {
    var ansTranscript = new Object();
    ansTranscript.id = transcript.transcript_id;
    ansTranscript.proteinId = transcript.protein.protein_id;
    ansTranscript.proteinLength = transcript.protein.length * 3 ;// in base units
    ansTranscript.proteinLengthInAA=transcript.protein.length;
    ansTranscript.description=transcript.protein.description;
    ansTranscript.proteinSynonyms=transcript.protein.synonyms;
    ansTranscript.proteinEnsemblID=transcript.protein.ensembl_id;
    ansTranscript.proteinUniprotID=transcript.protein.uniprot_id;
    ansTranscript.exons = [];
    ansTranscript.length = endCoordinate - startCoordinate;
    ansTranscript.maxProteinLength=maxProteinLength;
    var cdsStart=transcript.cds_start;
    ansTranscript.cds_start=cdsStart;
    var cdsEnd=transcript.cds_end;
    ansTranscript.cds_end=cdsEnd;
    ansTranscript.tx_start=transcript.tx_start;
    ansTranscript.tx_end=transcript.tx_end;
    ansTranscript.exonCount=transcript.exon_count;
    ansTranscript.ucsc_id=transcript.ucsc_id;
    ansTranscript.ensembl_id=transcript.ensembl_ID;
    ansTranscript.startCoordinate=startCoordinate; 
    ansTranscript.transcriptEnsemblLink=getEnsemblTranscriptLink(transcript.ensembl_ID,specie); 
    ansTranscript.proteinEnsemblLink=getEnsemblProteinLink(transcript.protein.ensembl_id,specie); 
    ansTranscript.genomicView=true;
    ansTranscript.transcriptView=true;
    ansTranscript.proteinView=true;
    ansTranscript.shownLength=proteinEnd-proteinStart;
    ansTranscript.proteinStart=proteinStart;

    //calculate things for each transcript
    for (var i = 0; i < transcript.transcriptExons.length; i++) {
        ansTranscript.exons[i] = new Object();
        ansTranscript.exons[i].transcriptViewStart = transcript.transcriptExons[i].genomic_start_tx - startCoordinate-1;  //-1  because it is zero based
        ansTranscript.exons[i].transcriptViewEnd = transcript.transcriptExons[i].genomic_end_tx - startCoordinate;
        ansTranscript.exons[i].exonViewStart = transcript.transcriptExons[i].abs_start_CDS-proteinStart;
        ansTranscript.exons[i].exonViewEnd = transcript.transcriptExons[i].abs_end_CDS-proteinStart;
        ansTranscript.exons[i].name =""// getGeneExonName(geneExons,transcript.transcriptExons[i].genomic_start,transcript.transcriptExons[i].genomic_end);
        ansTranscript.exons[i].id = transcript.transcriptExons[i].abs_end;
        ansTranscript.exons[i].color = geneExons[transcript.transcriptExons[i].genomic_start_tx][transcript.transcriptExons[i].genomic_end_tx].color;
        ansTranscript.exons[i].isUTRStart=undefined;
        ansTranscript.exons[i].isUTREnd=undefined;
        ansTranscript.exons[i].isUTRAll=false;
        ansTranscript.exons[i].orderInTranscript=transcript.transcriptExons[i].order_in_transcript;
        
        //finding utr for later drawings 
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
        ansTranscript.domains[i].start = domains[i].nuc_start-proteinStart;
        ansTranscript.domains[i].end = domains[i].nuc_end-proteinStart;
        ansTranscript.domains[i].name = domains[i].domainType.name;
        ansTranscript.domains[i].typeID = domains[i].domainType.type_id;
        ansTranscript.domains[i].overlap=false;
        ansTranscript.domains[i].showText=true;

    }
    findOverlaps(ansTranscript.domains);
    orderBySize(ansTranscript.domains);
    showNameOfDomains(ansTranscript.domains);

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

//finding the longest protein length so graphics will be measured according to it 
function findmaxProteinLength(transcripts){
    var maxProtein=0;
    for(var i=0; i<transcripts.length;i++){
        if( transcripts[i].protein.length>maxProtein){
            maxProtein=transcripts[i].protein.length;
        }
    }
    return maxProtein*3; //because we need length in nucleotides
}

//selecting color and related transcripts for each exon
function createGeneExonInfo(geneExons,geneTranscripts,ansGene,colorByLength){
    var exonInfo={};
    var exonForTable=[];
    var colorArr= ["#DACCFF", "#BBABF3","#B627FC",  "#DE3D3D", "#FF6262", "#f5b0cb", "#ffccd8", "#E8A089",
                
    "#deb881", "#c8965d","#FD9900", "#ffb90f", "#ffd700", "#FFFC3B", "#FFF599", "#FFFED3","#d1d797", "#ccff00", "#20F876", "#63C37F",
     "#beebe9", "#00ccff", "#A6B9B4", "#7BEAD2", "#180CF5"
];
    for( var i=0; i<geneExons.length;i++){
        if(exonInfo[geneExons[i].genomic_start_tx]==undefined){
            exonInfo[geneExons[i].genomic_start_tx]=[];
        }
        if(colorByLength){
            var chosenColor=getcolorByLength(colorArr,geneExons[i].genomic_end_tx-geneExons[i].genomic_start_tx);
        }else{
            var chosenColor=getcolorFromList(colorArr);
        }
        
        if(colorArr.length<2){
            colorArr= ["#DACCFF", "#BBABF3","#B627FC",  "#DE3D3D", "#FF6262", "#f5b0cb", "#ffccd8", "#E8A089",
                
            "#deb881", "#c8965d","#FD9900", "#ffb90f", "#ffd700", "#FFFC3B", "#FFF599", "#FFFED3","#d1d797", "#ccff00", "#20F876", "#63C37F",
             "#beebe9", "#00ccff", "#A6B9B4", "#7BEAD2", "#180CF5"
        ];
        }
        exonInfo[geneExons[i].genomic_start_tx][geneExons[i].genomic_end_tx]={color:chosenColor,name:""};
        var exonTranscripts=getTranscriptsForExon(geneExons[i].genomic_start_tx,geneExons[i].genomic_end_tx,geneTranscripts);
        if(exonTranscripts!=""){
            exonForTable.push({'transcripts':exonTranscripts,'startCoordinate':geneExons[i].genomic_start_tx,'endCoordinate':geneExons[i].genomic_end_tx,'color':chosenColor[0]});
        }
        
    }
    ansGene.exonTable=exonForTable;
    return exonInfo;
}

//checking for overlapping domains in positions. if it is overlapping at least once it is true
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

//sort *domains* by size
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

//when seeing overlapping domains it choses which one to show text to
function showNameOfDomains(domains){
    for(var i=0;i<domains.length;i++){
        
        for(var j=0;j<domains.length;j++){
            if(i==j){
                continue;
            }
            if(!(domains[i].showText && domains[j].showText)){ //one of them is not shown
                continue;
            }
            if (domains[i].start<=domains[j].start && domains[j].end<=domains[i].end ){
                domains[i].showText=false;
            }
            else if(domains[i].start<=domains[j].start && domains[i].end<=domains[j].end && domains[j].start<domains[i].end){
                domains[i].showText=false;
            }
        }
    }
}

//finding transcripts for each exon O(n*m) when n is number of transcripts and m number of exons
function getTranscriptsForExon(start,end,transcripts){
    var ans=""
    for(var i=0; i<transcripts.length;i++){
        for(var j=0;j<transcripts[i].transcriptExons.length;j++){
            if(transcripts[i].transcriptExons[j].genomic_start_tx==start &&transcripts[i].transcriptExons[j].genomic_end_tx==end){
                if(ans==""){
                    ans=transcripts[i].transcript_id;
                }else{
                    ans=ans+", "+transcripts[i].transcript_id;
                }
            }
        }
    }
    return ans;
}

//calculating ensemble transcript link
function getEnsemblTranscriptLink(ensembl_id,specie){
    return "https://www.ensembl.org/"+ensembleSpecieName(specie)+"/Transcript/Summary?db=core;t="+ensembl_id;
}

//calculating ensemble protein link
function getEnsemblProteinLink(ensembl_id,specie){
    return "https://www.ensembl.org/"+ensembleSpecieName(specie)+"/Transcript/ProteinSummary?db=core;p="+ensembl_id;
}

//this function returns the right specie name as it is in Ensembl
function ensembleSpecieName(specie){
    if(specie=="M_Musculus"){
        return "Mus_musculus";
    }else if(specie=="H_sapiens"){
        return "Homo_sapiens";
    }
    return undefined;
}

//calculating ensemble gene link
function getEnsemblGeneLink(ensembl_id,specie){
    return "https://www.ensembl.org/"+ensembleSpecieName(specie)+"/Gene/Summary?db=core;g="+ensembl_id;
}

//TODO? is it used? might delete
function runGenesCreationTry2(result,ignorePredictions){
    var geneList=[];

    for(var i=0; i<result.genes.length;i++){
        geneList.push(createGraphicInfoForGene(result.genes[i],ignorePredictions));
    }
    return geneList;
}

function getSpecieName(specie){
    if(specie=="M_musculus"){
        return "(Mouse, mm10)"
    }
    if(specie=="H_sapiens"){
        return "(Human, hg38)"
    }
    if(specie=="R_norvegicus"){
        return "(Rat, rn6)"
    }
    if(specie=="D_rerio"){
        return "(Zebrafish, danRer11)"
    }
    if(specie=="X_tropicalis"){
        return "(Frog, xenTro9)"
    }
    return undefined;
}
