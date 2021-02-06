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

        this.locationScopeChanger = new Object();

        //in the beginning this needs to be called and the result should be in the html tag in the class property
        this.locationScopeChanger.getChangerClassForStrand = function(strand){
            if(strand=='+'){
                return "js-range-slider";
            }else{
                return "js-range-slider-reverse-fixed";
            }
        }

        this.locationScopeChanger.updateGenomiclocationScopeChanger = function (name, scale, strand, onFinishWhenStrandPositive, onFinishWhenStrandNegative, maximumRange, minimumRange) {
            var minVal = undefined;
            var maxVal = undefined;
            var fromVal = undefined;
            var toVal = undefined;
            var prettifyVal = undefined;
            var onFinishVal = undefined;

            if (strand == '+') {
                minVal = scale.start;
                maxVal = scale.end;
                fromVal = scale.start;
                toVal = scale.end;
                prettifyVal = function (num) {
                    return num;
                };
                onFinishVal = onFinishWhenStrandPositive;
            } else {
                    // var maximumRange=self.geneInfo.end;
                    // var minimumRange=self.geneInfo.start;

                    minVal = minimumRange - minimumRange, /*min - min*/
                    maxVal = maximumRange - minimumRange, /*max - min*/
                    fromVal = maximumRange - scale.end, /*max - to*/
                    toVal = maximumRange - scale.start, /*max - from*/
                    prettifyVal = function (num) {
                        return maximumRange - num; /*max - num*/
                    },
                    onFinishVal = onFinishWhenStrandNegative;
            }

            $(name).ionRangeSlider({
                type: "double",
                skin: "square",
                min: minVal,
                max: maxVal,
                from: fromVal,
                to: toVal,
                prettify: prettifyVal,
                drag_interval: true,
                onFinish: onFinishVal
            });
        }
    }
}