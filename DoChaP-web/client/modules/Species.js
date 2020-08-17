class Species {

    constructor() {}
    /**
     * 
     * @param {string} source the source id (the beginning of it can be used to find the source)
     */
    static getURLfor(source) {
        if (source.substring(0, 5) == 'smart') {
            return "http://smart.embl-heidelberg.de/smart/do_annotation.pl?DOMAIN=" + source.substring(5);
        }
        if (source.substring(0, 4) == 'pfam') {
            return "https://pfam.xfam.org/family/" + 'PF' + source.substring(4);
        }
        if (source.substring(0, 2) == 'cd') {
            return "https://www.ncbi.nlm.nih.gov/Structure/cdd/cddsrv.cgi?uid=" + source;
        }
        if (source.substring(0, 4) == 'TIGR') {
            return "http://tigrfams.jcvi.org/cgi-bin/HmmReportPage.cgi?acc=" + source;
        }
        if (source.substring(0, 3) == 'IPR') {
            return "https://www.ebi.ac.uk/interpro/entry/InterPro/" + source+ '/';
        }
        return "https://www.ncbi.nlm.nih.gov/Structure/cdd/" + source
    }



    /**
     * this function returns the right specie name as it is in Ensembl
     * @param {String} specie specie name in the db
     */
    static ensembleSpecieName(specie) {
        if (specie == "M_musculus") {
            return "Mus_musculus";
        } else if (specie == "H_sapiens") {
            return "Homo_sapiens";
        } else if (specie == "X_tropicalis") {
            return "Xenopus_tropicalis";
        } else if (specie == "D_rerio") {
            return "Danio_rerio";
        } else if (specie == "R_norvegicus") {
            return "Rattus_norvegicus";
        }
        return undefined;
    }
    /**
     * this function returns the specie name for showing users
     * @param {String} specie specie name in the db
     */
    static getSpecieName(species) {
        if (species== "M_musculus") {
            return "(Mouse, mm10)"
        }
        if (species == "H_sapiens") {
            return "(Human, hg38)"
        }
        if (species == "R_norvegicus") {
            return "(Rat, rn6)"
        }
        if (species == "D_rerio") {
            return "(Zebrafish, danRer11)"
        }
        if (species == "X_tropicalis") {
            return "(Frog, xenTro9)"
        }
        return undefined;
    }


    static isNotID(source){
        if (source.substring(0, 5) == 'smart'
        || source.substring(0, 4) == 'pfam' || source.substring(0, 2) == 'cd'
         || source.substring(0, 4) == 'TIGR'
         || source.substring(0, 3) == 'IPR') {
            return true;
        }
        return false;
    }
}