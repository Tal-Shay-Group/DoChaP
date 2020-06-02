/**
 * this class implemants cache with dictionary that 
 * know to rank the records and delete the irrelevant records 
 * each time it is full
 */
class QueryCache {
    constructor() {
        this.cache = {}; //holds data
        this.cachePoints = {}; // holds points(rank of importantness)
        this.lengthLimit = 30; //for cache
    }

    addNewQuery(id, res) {
        if (this.cacheAlmostFull()) {
            this.deleteIrrelevantRecords();
        }
        this.cache[id] = res;
        this.cachePoints[id] = 0;
    }

    getIfExists(queryID) {
        if (this.cache[queryID] != undefined) {
            //add point and return the found record
            this.cachePoints[queryID] = Math.min(this.lengthLimit - 1, this.cachePoints[queryID] + 1);
            return this.cache[queryID];
        }
        return undefined;
    }

    cacheAlmostFull() {
        return Object.keys(this.cache).length >= this.lengthLimit;
    }


    deleteIrrelevantRecords() {
        var loop = true;

        for (var i = 0; i < this.lengthLimit && loop; i++) {
            var toDelete = [];
            //find
            for (var key in this.cache) {
                if (this.cachePoints[key] == i) {
                    toDelete.push(key);
                }
            }
            //delete
            for (var j = 0; j < toDelete.length; j++) {
                delete this.cache[toDelete[j]];
                delete this.cachePoints[toDelete[j]];
            }
            if (Object.keys(this.cache).length <= this.lengthLimit * (2 / 3)) {
                loop = false;
            }

        }
        console.log("deleted unused from cache. now there are only " + Object.keys(this.cache).length);
    }

}
exports.qCache = new QueryCache();