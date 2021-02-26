class TranscriptDisplayManager {
    constructor() {
    }
    addTranscripts(transcripts) {
        this.transcripts = transcripts;
    }
    hideTranscriptByIndex(index) {
        var transcripts = this.transcripts;
        transcripts[index].genomicView = false;
        transcripts[index].transcriptView = false;
        transcripts[index].proteinView = false;
    };
    showTranscript(index, viewMode) {
        if (viewMode === "genomic") {
            this.transcripts[index].genomicView = true;
            this.transcripts[index].transcriptView = false;
            this.transcripts[index].proteinView = false;
        } else if (viewMode === "transcript") {
            this.transcripts[index].genomicView = false;
            this.transcripts[index].transcriptView = true;
            this.transcripts[index].proteinView = false;
        } else if (viewMode === "protein") {
            this.transcripts[index].genomicView = false;
            this.transcripts[index].transcriptView = false;
            this.transcripts[index].proteinView = true;
        } else if (viewMode === "all") {
            this.transcripts[index].genomicView = true;
            this.transcripts[index].transcriptView = true;
            this.transcripts[index].proteinView = true;
        } else if (viewMode === "transcript_protein") {
            this.transcripts[index].genomicView = false;
            this.transcripts[index].transcriptView = true;
            this.transcripts[index].proteinView = true;
        }
    };
    
    changeViewMode(newViewMode) {
        for (var index = 0; index < this.transcripts.length; index++) {
            if (this.isTranscriptShownByIndex(index)) {
                this.showTranscript(index, newViewMode)
            }
        }
    };
    isTranscriptShownByIndex(index) {
        if ((this.transcripts[index].genomicView) ||
            (this.transcripts[index].transcriptView) ||
            (this.transcripts[index].proteinView)) {
            return true;
        }

        return false;
    }
    
    countShownTranscripts() {
        var results = new Object();
        var counter = 0;

        for (var i = 0; i < this.transcripts.length; i++) {
            if (this.isTranscriptShownByIndex(i)) {
                counter = counter + 1;
            }
        }

        results.shownTranscripts = counter;
        results.hiddenTranscripts = this.transcripts.length - counter;
        return results;
    }
}