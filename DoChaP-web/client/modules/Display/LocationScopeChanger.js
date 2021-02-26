class LocationScopeChanger {
    constructor() {
    }
    
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

}