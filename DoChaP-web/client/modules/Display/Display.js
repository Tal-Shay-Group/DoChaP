class Display {
    constructor() {
        this.modal = new Modal();
        this.locationScopeChanger = new LocationScopeChanger();
        this.pdfCreator = new PdfCreator();
        this.transcriptDisplayManager = new TranscriptDisplayManager();
        this.canvasUpdater = new CanvasUpdater();
    };
}