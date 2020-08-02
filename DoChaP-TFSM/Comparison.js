class Comparison {
    constructor(firstElement, secondElement, comparator, drawer, weights) {
        this.firstElement = firstElement;
        this.secondElement = secondElement;
        this.compartor = comparator;
        this.drawer = drawer;
        this.weights = weights;
    }
    search() {
        this.drawer.draw(this.compartor.compare(this.firstElement, this.secondElement, this.weights));
    }
}