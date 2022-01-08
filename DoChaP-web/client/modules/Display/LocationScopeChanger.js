class LocationScopeChanger {
    constructor() {}

    getChangerClassForStrand(strand) {
        if (strand == '+') {
            return "js-range-slider";
        } else {
            return "js-range-slider-reverse-fixed";
        }
    }

    updateGenomiclocationScopeChanger(name, scale, strand, onFinishWhenStrandPositive, onFinishWhenStrandNegative, maximumRange, minimumRange) {
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

    updateProteinlocationScopeChanger(name, onFinish, maximumRange) {
        $(name).ionRangeSlider({
            type: "double",
            min: 0,
            max: maximumRange,
            from: 0,
            to: maximumRange,
            drag_interval: true,
            skin: "square",
            onFinish: onFinish
        });
    }

    zoomGenomicWithButton(strand, scale, zoomDirection, onFinishWhenStrandPositive, onFinishWhenStrandNegative, rangeSliderName, gene) {
        let length = scale.end - scale.start;
        
        let zoomedAreaFromEachSide = length * 0.1;
        if (zoomDirection == "Out") {
            zoomedAreaFromEachSide = -length * 0.1;
        }
        let start =scale.start + zoomedAreaFromEachSide;
        let end = scale.end - zoomedAreaFromEachSide;
        this.moveToSelectedGenomicRange(strand, rangeSliderName, start, end, onFinishWhenStrandPositive, onFinishWhenStrandNegative, gene);
    }

    moveToSelectedGenomicRange(strand, rangeSliderName, start, end, onFinishWhenStrandPositive, onFinishWhenStrandNegative, gene){
        start = Math.max(gene.initStart, start);
        end = Math.min(gene.initEnd, end);
        
        if (strand == "+") {
            $(rangeSliderName).data("ionRangeSlider").update({
                from: start,
                to: end
            });
            onFinishWhenStrandPositive({
                "from": start,
                "to": end
            });
        } else if (strand == "-") {
            $(rangeSliderName).data("ionRangeSlider").update({
                from: gene.initEnd - end,
                to: gene.initEnd - start
            });
            onFinishWhenStrandNegative({
                "from": gene.initEnd - end,
                "to": gene.initEnd - start
            });
        }
    }

    zoomProteinWithButton(scale, zoomDirection, onProteinFinish, rangeSliderName) {
        let length = scale.zoomInEnd - scale.zoomInStart;
        
        let zoomedAreaFromEachSide = length * 0.1;
        if (zoomDirection == "Out") {
            zoomedAreaFromEachSide = -length * 0.1;
        }
        
        let start = Math.max(0, scale.zoomInStart + zoomedAreaFromEachSide);
        let end = Math.min(scale.length, scale.zoomInEnd - zoomedAreaFromEachSide);
        
        $(rangeSliderName).data("ionRangeSlider").update({
            from: start,
            to: end
        });
        onProteinFinish({
            "from": start,
            "to": end
        });
    }

}