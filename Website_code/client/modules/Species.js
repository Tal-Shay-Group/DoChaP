class Species {
    
    constructor() {
    }

    static getURLfor(source) {
        if(source.substring(0,5)=='smart'){
            return "http://smart.embl-heidelberg.de/smart/do_annotation.pl?DOMAIN="+source;
        }
        if(source.substring(0,4)=='pfam'){
            return "https://pfam.xfam.org/family/"+'PF'+source.substring(4);
        }
        if(source.substring(0,2)=='cd'){
            return "https://www.ncbi.nlm.nih.gov/Structure/cdd/cddsrv.cgi?uid="+source;
        }
        if(source.substring(0,4)=='TIGR'){
            return "http://tigrfams.jcvi.org/cgi-bin/HmmReportPage.cgi?acc="+source;
        }
        return "https://www.ncbi.nlm.nih.gov/Structure/cdd/" + source
    }

    //this function returns the right specie name as it is in Ensembl
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
}