class Display {
    constructor() {
        this.modal = new Object();
        this.modal.type = undefined;
        this.modal.openWindow = function (type, currentTranscript) {
            $('#BlackBackground').css('display', 'block');
            this.type = type;
            if (type == "transcript") {
                currentTranscript.tx_start = numberToTextWithCommas(currentTranscript.tx_start);
                currentTranscript.tx_end = numberToTextWithCommas(currentTranscript.tx_end);
                currentTranscript.cds_start = numberToTextWithCommas(currentTranscript.cds_start);
                currentTranscript.cds_end = numberToTextWithCommas(currentTranscript.cds_end);
            }
        };

        this.modal.closeWindowFromTheSide =  function (event) {
            if (event.target.id == 'BlackBackground') {
                this.type = undefined;
            }
        }

        var locationScopeChanger = new Object();
    }

}