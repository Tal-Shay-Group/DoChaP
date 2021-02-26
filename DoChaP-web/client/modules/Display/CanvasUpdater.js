class CanvasUpdater {
    constructor() {
        this.isStart  = true;
    }
  
    updateCanvas(gene, tooltipManager, idForCanvas, scope) {
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
                        Domain.domainClick(tooltipManager, event);
                        scope.$apply();
                    });
                scope.$apply();
            });
        }
}