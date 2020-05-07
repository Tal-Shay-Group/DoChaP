class Gene {
    /**
     * 
     * @param {gene row from db} dbGene 
     * @param {boolean} ignorePredictions if to ignore RefSeq transcripts with XM
     * @param {array of colors or undefined} colorByLength colors to color exons if exists and wanted. mostly for compare species
     * @param {double} start zoom in start for genomic axis
     * @param {double} end zoom in end for genomic axis
     * @param {double} proteinStart zoom in start for protein axis
     * @param {double} proteinEnd zoom in end for protein axis
     */
    constructor(dbGene, ignorePredictions, colorByLength, start, end, proteinStart, proteinEnd) {
        //gene symbol where only the first letter is capitalized
        this.gene_symbol = dbGene.gene_symbol.toUpperCase().substring(0, 1) + dbGene.gene_symbol.toLowerCase().substring(1);

        //basic attributes from db
        this.gene_GeneID_id = dbGene.gene_GeneID_id;
        this.strand = dbGene.strand;
        this.synonyms = dbGene.synonyms;
        this.chromosome = dbGene.chromosome;
        this.description = dbGene.description;
        this.MGI_id = dbGene.MGI_id;
        this.gene_ensembl_id = dbGene.gene_ensembl_id;
        this.specie = dbGene.specie;
        this.colorByLength=colorByLength;
        this.ignorePredictions=ignorePredictions;//to filter refseq unreviewed

        //calculated attributes
        this.specieName = this.getSpecieName();
        this.EnsemblLink = this.getEnsemblGeneLink();
        this.geneExons = this.createGeneExonInfo(dbGene.geneExons, dbGene.transcripts, colorByLength);
        this.maxProteinLength = this.findmaxProteinLength(dbGene.transcripts);
     
        //zoom in options (if given as arguments)
        this.start = start ? start : this.findStartCoordinate(dbGene.transcripts);
        this.end = end ? end : this.findEndCoordinate(dbGene.transcripts);
        this.proteinStart = proteinStart ? proteinStart : 0;
        this.proteinEnd = proteinEnd ? proteinEnd : this.findmaxProteinLength(dbGene.transcripts);

        //for long introns. we find if we can cut them
        this.checkForLongIntronsToCut(dbGene.geneExons);

        //push transcripts
        this.transcripts = [];
        for (var i = 0; i < dbGene.transcripts.length; i++) {
            if (ignorePredictions == false || dbGene.transcripts[i].transcript_refseq_id==undefined || (dbGene.transcripts[i].transcript_refseq_id!=undefined &&dbGene.transcripts[i].transcript_refseq_id.substring(0, 2) == "NM")) {
                this.transcripts.push(new Transcript(dbGene.transcripts[i],this));
            }
        }
        this.transcripts = this.transcripts.sort(Transcript.compare);

        //scales
        this.scale = new GenomicScale(this);
        this.proteinScale = new ProteinScale(this.maxProteinLength, this.proteinStart, this.proteinEnd);
    }

    /**
     * finds start coordinates by finding the 'earliest coordinate' mentioned from all transcripts of this gene
     * @param {array of Transcript} transcripts 
     */
    findStartCoordinate(transcripts) {
        var minStartPoint = transcripts[0].tx_start; // implying there is at least one transcript . if there is infinity it would be better for init 
        for (var i = 0; i < transcripts.length; i++) {
            if (minStartPoint > transcripts[i].tx_start) {
                minStartPoint = transcripts[i].tx_start;
            }
        }
        return minStartPoint;
    }

    /**
     * finds end coordinates by finding the 'latest coordinate' mentioned from all transcripts of this gene
     * @param {array of Transcript} transcripts 
     */
    findEndCoordinate(transcripts) {
        var endPoint = transcripts[0].tx_end; // implying there is at least one transcript . if there is infinity it would be better for init 
        for (var i = 0; i < transcripts.length; i++) {
            if (endPoint < transcripts[i].tx_end) {
                endPoint = transcripts[i].tx_end;
            }
        }
        return endPoint;
    }

    /**
     * finding the longest protein length so graphics will be measured according to it
     * @param {array of Transcript} transcripts 
     */
    findmaxProteinLength(transcripts) {
        var maxProtein = 0;
        for (var i = 0; i < transcripts.length; i++) {
            if (transcripts[i].protein.length > maxProtein) {
                maxProtein = transcripts[i].protein.length;
            }
        }
        return maxProtein * 3; //because we need length in nucleotides
    }

    /**
     * selecting color and related transcripts for each exon
     * @param {*} geneExons 
     * @param {*} geneTranscripts 
     * @param {*} colorByLength 
     */
    createGeneExonInfo(geneExons, geneTranscripts, colorByLength) {
        var exonInfo = {};
        var exonForTable = [];
        var colorArr = []; //initialized with colors when used in function
        for (var i = 0; i < geneExons.length; i++) {
            if (exonInfo[geneExons[i].genomic_start_tx] == undefined) {
                exonInfo[geneExons[i].genomic_start_tx] = [];
            }
            if (colorByLength != undefined) {
                var chosenColor = colorByLength[geneExons[i].genomic_end_tx - geneExons[i].genomic_start_tx];
            } else {
                var chosenColor = getcolorFromList(colorArr);
            }
            exonInfo[geneExons[i].genomic_start_tx][geneExons[i].genomic_end_tx] = {
                color: chosenColor,
                name: ""
            };
            var exonTranscripts = this.getTranscriptsForExon(geneExons[i].genomic_start_tx, geneExons[i].genomic_end_tx, geneTranscripts);
            if (exonTranscripts != "") {
                exonForTable.push({
                    'transcripts': exonTranscripts,
                    'startCoordinate': geneExons[i].genomic_start_tx,
                    'endCoordinate': geneExons[i].genomic_end_tx,
                    'color': chosenColor
                });
            }

        }
        this.exonTable = exonForTable;
        return exonInfo;
    }

    /**
     * finding transcripts for each exon O(n*m) when n is number of transcripts and m number of exons
     * @param {*} start 
     * @param {*} end 
     * @param {*} transcripts 
     */
    getTranscriptsForExon(start, end, transcripts) {
        var ans = ""
        for (var i = 0; i < transcripts.length; i++) {
            if (this.ignorePredictions == true && transcripts[i].transcript_refseq_id!=undefined && transcripts[i].transcript_refseq_id.substring(0, 2) == "XM") {
                continue;
            }
            for (var j = 0; j < transcripts[i].transcriptExons.length; j++) {
                if (transcripts[i].transcriptExons[j].genomic_start_tx == start && transcripts[i].transcriptExons[j].genomic_end_tx == end) {
                    var name=transcripts[i].transcript_refseq_id;
                    if(name==undefined){
                        name=transcripts[i].transcript_ensembl_id;
                    }
                    if (ans == "") {
                        ans = name;
                    } else {
                        ans = ans + ", " + name;
                    }
                }
            }
        }
        return ans;
    }

    //calculating ensemble gene link
    getEnsemblGeneLink() {
        return "https://www.ensembl.org/" + Species.ensembleSpecieName(this.specie) + "/Gene/Summary?db=core;g=" + this.gene_ensembl_id;
    }

    getSpecieName() {
        if (this.specie == "M_musculus") {
            return "(Mouse, mm10)"
        }
        if (this.specie == "H_sapiens") {
            return "(Human, hg38)"
        }
        if (this.specie == "R_norvegicus") {
            return "(Rat, rn6)"
        }
        if (this.specie == "D_rerio") {
            return "(Zebrafish, danRer11)"
        }
        if (this.specie == "X_tropicalis") {
            return "(Frog, xenTro9)"
        }
        return undefined;
    }

    //note that it is also depends on start  and end(zoom in chosen)
    checkForLongIntronsToCut(geneExons) {
        var exons = geneExons.sort((a, b) => {
            a.genomic_start_tx - b.genomic_start_tx
        });

        this.cutOffStart=-1;
        this.cutOffLength=-1;
        if(exons.length<1){
            return;
        }

        //find prev 
        var prev = -1;
        for (var i = 0; i < exons.length; i++) {
            //if not seen after zoom you can skip it
            if(exons[i].genomic_start_tx>this.end || exons[i].genomic_end_tx<this.start){
                continue;
            }
            //if got here it is the first
            prev=exons[i].genomic_end_tx;
            break;
        }

        //no exons found in need for introns to cut.
        if(prev==-1){
            return;
        }


        var start=-1;
        var length=-1;
        for (var i = 0; i < exons.length; i++) {

            //if not seen after zoom you can skip it
            if(exons[i].genomic_start_tx>this.end || exons[i].genomic_end_tx<this.start){
                continue;
            }
            
            //if there is a big intron
            if(exons[i].genomic_start_tx>prev+1000000){  //milion nuclotides difference
                start=prev
                length=exons[i].genomic_start_tx-prev;
                break;
            }
            prev=Math.max(prev,exons[i].genomic_end_tx);
        }

        if(start!= -1 && length!= -1){
            if(start<this.start || start+length >this.end){
                window.alert("error normalizing big introns.");
            }
            this.cutOffStart=start;
            this.cutOffLength=length;
        }
    }


}