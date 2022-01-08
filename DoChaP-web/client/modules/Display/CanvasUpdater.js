class CanvasUpdater {
    constructor() {
        this.isStart = true;
    }

    updateCanvas(gene, tooltipManager, idForCanvas, $scope) {
        $(document).ready(function () {
            //drawing all transcripts
            for (var i = 0; i < gene.transcripts.length; i++) {
                if (this.isStart) {
                    $('#fadeinDiv' + idForCanvas + i).hide().fadeIn(1000 + Math.min(i * 500, 1000));

                }
                gene.transcripts[i].show('canvas-genomic' + idForCanvas + i, 'canvas-transcript' + idForCanvas + i, 'canvas-protein' + idForCanvas + i, tooltipManager, 'canvas-protein-extend' + idForCanvas + i);
            }
            this.isStart = false;

            //drawing scales
            gene.scale.draw("canvas-scale" + idForCanvas);
            gene.scale.drawBehind("genomicGridlines" + idForCanvas);
            gene.proteinScale.drawBehind("proteinGridlines" + idForCanvas);
            gene.proteinScale.draw("canvas-scale-protein" + idForCanvas);

            //click for extended protein view
            $("canvas")
                .click(function (event) {
                    if (event.target.id.substring(0,14)==="canvas-protein") {
                        CanvasUpdater.onDomainClickEvent(tooltipManager, event);
                        $scope.$apply();
                    } else if (event.target.id.substring(0,14)==="canvas-genomic") {
                        CanvasUpdater.onExonZoomEvent(tooltipManager, event, $scope);
                        $scope.$apply();
                    }
                });
            $scope.$apply();
        });
    }
    /**
     * when click on domain opening/closing fourth view in the tooltipManager
     * @param {tooltipManager} tooltipManager has values of each domain info and positions
     * @param {event} event click-event
     */
    static onDomainClickEvent(tooltipManager, event) {
        var showTextValues = Transcript.showText(event, tooltipManager);
        if (showTextValues[0]) {
            if (showTextValues[2] == 'click' && tooltipManager[event.target.id + "object"] != undefined) { //if has a fourthview (means domains overlap enough)
                tooltipManager[event.target.id + "object"].proteinExtendView = !tooltipManager[event.target.id + "object"].proteinExtendView;
            }

        }
    }

    static onExonZoomEvent(tooltipManager, event, $scope) {
        var showTextValues = Transcript.showText(event, tooltipManager);

        if (showTextValues[3] != undefined) { // When does this happen? I think when it is genomic view?
            var proteinStart = showTextValues[3].abs_start_CDS;
            var proteinEnd = showTextValues[3].abs_end_CDS;
            var genomicStart = showTextValues[3].genomic_start_tx;
            var genomicEnd = showTextValues[3].genomic_end_tx

            if ($scope.onExonClick != undefined) {
                $scope.onExonClick(proteinStart - 1, proteinEnd, genomicStart, genomicEnd);
            }

        }
    }
}