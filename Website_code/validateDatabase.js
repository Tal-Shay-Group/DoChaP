var DButils = require('./DButils');

///main: !!
//runTestsOnDB();
//end main




//connects to the db using db module (DButils) and returns query answer
function sqlQuery(query) {
    var promise = new Promise(function (resolve, reject) {
        DButils.db.all(query, [], async (err, rows) => {
            if (err == undefined) {
                resolve(rows);
            }
            else {
                reject(err);
            }
        });
    });
    return promise;
}

async function runTestsOnDB(){
    console.log("running a program to find unusual data in our db");
    await runExonsInTranscriptsStatistics();
    console.log("**********\n");
    await runTranscriptsInGeneStatistics();
    console.log("**********\n");
    await runDomainFrequencyStatistics();
    console.log("**********\n");
    await runCdsAndTxCheck();
    console.log("**********\n");
    await runStartAndEndCheck(); //exons 
    console.log("**********\n");
    await runProteinSizeCheck();
    console.log("**********\n");
    await runSmallSizedDomains();
    console.log("**********\n");
    console.log("finished running!");
}
async function typesOfDomainsCut(){
    /*sql if needed:
    drop table if exists tempt1;
    drop table if exists tempt2;
    drop table if exists tempt3;
    drop table if exists tempt4;
    create temporary table tempt1 as
    select type_id,count() from SpliceInDomains group by type_id;
    create temporary table tempt2 as
    select type_id from DomainType except select type_id from SpliceInDomains;
    create temporary table tempt3 as
    select type_id from DomainType except select type_id from SpliceInDomains;
    create temporary table tempt4 as
    select type_id,0 from tempt3;

    select * from tempt1 union select * from tempt4 ;


    */
    var results=await sqlQuery("drop table if exists tempt1;"+
    "drop table if exists tempt2;"+
    "drop table if exists tempt3;"+
    "drop table if exists tempt4;"+
    "create temporary table tempt1 as"+
    "select type_id,count() from SpliceInDomains group by type_id;"+
    "create temporary table tempt2 as"+
    "select type_id from DomainType except select type_id from SpliceInDomains;"+
    "create temporary table tempt3 as"+
    "select type_id from DomainType except select type_id from SpliceInDomains;"+
    "create temporary table tempt4 as"+
    "select type_id,0 from tempt3;"+
    
    "select * from tempt1 union select * from tempt4 ;");

    for(var i=0;i<results.length;i++){
        console.log(results[i][0]+","+results[i][1]);
    }

}


function cutIntronsPercent(){
    /*
sql
    drop table if exists tempt1;
    drop table if exists tempt2;
    create temporary table tempt1 as
    select protein_id,length from Proteins limit 1000;
    create temporary table tempt2 as
    select protein_id, AA_start, AA_end from DomainEvent;
    select tempt1.protein_id, AA_start, AA_end, length from tempt1,tempt2 where tempt1.protein_id=tempt2.protein_id
    
    in the end used:
    drop table if exists tempt1;
    drop table if exists tempt2;
    create temporary table tempt1 as
    select protein_id,length from Proteins limit 1000;
    create temporary table tempt2 as
    select protein_id, AA_start, AA_end from DomainEvent;
    select tempt1.protein_id, sum(AA_end)-sum(AA_start) as domainSpace, length from tempt1,tempt2 where tempt1.protein_id=tempt2.protein_id group by tempt1.protein_id 
    
    
    */
    //var domains=await sqlQuery(
    //"drop table if exists tempt1;  drop table if exists tempt2;   create temporary table tempt1 as    select protein_id,length from Proteins limit 1000;    create temporary table tempt2 as    select protein_id, AA_start, AA_end from DomainEvent; select tempt1.protein_id, sum(AA_end)-sum(AA_start) as domainSpace, length from tempt1,tempt2 where tempt1.protein_id=tempt2.protein_id group by tempt1.protein_id");
    //for (var i=0;)
}
async function runExonsInTranscriptsStatistics(){
    var results=await sqlQuery(
    "select count(transcript_id), exon_count "
    +"from transcripts "
    +"group by exon_count"
    );
    //in python we can create also a graph
    var count0=0;
    var count1=0;
    var count2=0;
    var count3=0;
    var count4=0;
    var count5=0;
    var count6to9=0;
    var count10to15=0;
    var count16to35=0;
    var count36andMore=0;

    for(var i=0; i<results.length;i++){
        if(results[i].exon_count==0){
            count0=count0+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count==1){
            count1=count1+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count==2){
            count2=count2+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count==3){
            count3=count3+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count==4){
            count4=count4+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count==5){
            count5=count5+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count>=6 && results[i].exon_count<=9 ){
            count6to9=count6to9+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count>=10 && results[i].exon_count<=15 ){
            count10to15=count10to15+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count>=16 && results[i].exon_count<=35){
            count16to35=count16to35+results[i]["count(transcript_id)"];
        } else if(results[i].exon_count>=36){
            count36andMore=count36andMore+results[i]["count(transcript_id)"];
        } else{
            console.log("exon count not indexed"+results[i].exon_count);
        }
       
    }
    console.log("transcripts with 0 exons: "+count0);
    console.log("transcripts with 1 exons: "+count1);
    console.log("transcripts with 2 exons: "+count2);
    console.log("transcripts with 3 exons: "+count3);
    console.log("transcripts with 4 exons: "+count4);
    console.log("transcripts with 5 exons: "+count5);
    console.log("transcripts with 6 to 9 exons: "+count6to9);
    console.log("transcripts with 10 to 15 exons: "+count10to15);
    console.log("transcripts with 16 to 35 exons: "+count16to35);
    console.log("transcripts with 36+ exons: "+count36andMore);

    var total= count0+ count1+count2+count3+count4+count5+count6to9+count10to15+count16to35+count36andMore;
    console.log("total: "+total);
}

async function runTranscriptsInGeneStatistics(){
    var results=await sqlQuery("select count(transcript_id) from transcripts group by gene_id");
        //in python we can create also a graph
        var count0=0;
        var count1=0;
        var count2=0;
        var count3=0;
        var count4=0;
        var count5=0;
        var count6to15=0;
        var count16to35=0;
        var count36andMore=0;
    
        for(var i=0; i<results.length;i++){
            if(results[i]["count(transcript_id)"]==0){
                count0=count0+1;
            } else if(results[i]["count(transcript_id)"]==1){
                count1=count1+1;
            } else if(results[i]["count(transcript_id)"]==2){
                count2=count2+1;
            } else if(results[i]["count(transcript_id)"]==3){
                count3=count3+1;
            } else if(results[i]["count(transcript_id)"]==4){
                count4=count4+1;
            } else if(results[i]["count(transcript_id)"]==5){
                count5=count5+1;
            } else if(results[i]["count(transcript_id)"]>=6 && results[i]["count(transcript_id)"]<=15 ){
                count6to15=count6to15+1;
            } else if(results[i]["count(transcript_id)"]>=16 && results[i]["count(transcript_id)"]<=35){
                count16to35=count16to35+1;
            } else if(results[i]["count(transcript_id)"]>=36){
                count36andMore=count36andMore+1;
            } else{
                console.log("exon count not indexed"+results[i]["count(transcript_id)"]);
            }
           
        }
    
        console.log("genes with 0 transcripts: "+count0);
        console.log("genes with 1 transcript: "+count1);
        console.log("genes with 2 transcripts: "+count2);
        console.log("genes with 3 transcripts: "+count3);
        console.log("genes with 4 transcripts: "+count4);
        console.log("genes with 5 transcripts: "+count5);
        console.log("genes with 6 to 15 transcripts: "+count6to15);
        console.log("genes with 16 to 35 transcripts: "+count16to35);
        console.log("genes with 36+ transcripts: "+count36andMore);
    var total= count0+ count1+count2+count3+count4+count5+count6to15+count16to35+count36andMore;
    console.log("total: "+total);
}

async function runDomainFrequencyStatistics(){
    var results=await sqlQuery("select count(*) from DomainEvent group by type_id");
    //in python we can create also a graph
    var count0=0;
    var count1=0;
    var count2=0;
    var count3=0;
    var count4=0;
    var count5=0;
    var count6to15=0;
    var count16to35=0;
    var count36andMore=0;

    for(var i=0; i<results.length;i++){
        if(results[i]["count(*)"]==0){
            count0=count0+1;
        } else if(results[i]["count(*)"]==1){
            count1=count1+1;
        } else if(results[i]["count(*)"]==2){
            count2=count2+1;
        } else if(results[i]["count(*)"]==3){
            count3=count3+1;
        } else if(results[i]["count(*)"]==4){
            count4=count4+1;
        } else if(results[i]["count(*)"]==5){
            count5=count5+1;
        } else if(results[i]["count(*)"]>=6 && results[i]["count(*)"]<=15 ){
            count6to15=count6to15+1;
        } else if(results[i]["count(*)"]>=16 && results[i]["count(*)"]<=35){
            count16to35=count16to35+1;
        } else if(results[i]["count(*)"]>=36){
            count36andMore=count36andMore+1;
        } else{
            console.log("exon count not indexed"+results[i]["count(*)"]);
        }
       
    }

    console.log("domain types with 0 domain events: "+count0);
    console.log("domain types with 1 domain events: "+count1);
    console.log("domain types with 2 domain events: "+count2);
    console.log("domain types with 3 domain events: "+count3);
    console.log("domain types with 4 domain events: "+count4);
    console.log("domain types with 5 domain events: "+count5);
    console.log("domain types with 6 to 15 domain events: "+count6to15);
    console.log("domain types with 16 to 35 domain events: "+count16to35);
    console.log("domain types with 36+ domain events: "+count36andMore);
    
    var total= count0+ count1+count2+count3+count4+count5+count6to15+count16to35+count36andMore;
    console.log("total: "+total);
}

async function runCdsAndTxCheck(){
    var results1=await sqlQuery("select * from transcripts where tx_start+3>=tx_end");
    var results2=await sqlQuery("select * from transcripts where cds_start+3>=cds_end");
    var results3=await sqlQuery("select * from transcripts where tx_start+3>=cds_start");
    var results4=await sqlQuery("select * from transcripts where tx_end+3<=cds_end");
    
    console.log("tx length about 3 or less: "+results1.length); //check how length is calculated here
    console.log("cds length about 3 or less: "+results2.length);
    console.log("utr in start is about 3 or less: "+results3.length);
    console.log("utr in end is about 3 or less: "+results4.length);

}

async function runStartAndEndCheck(){ //check exons and domains and maybe split in domains
    var results=await sqlQuery("select genomic_start_tx, genomic_end_tx from exons where genomic_start_tx+4>=genomic_end_tx");
    var count0=0;
    var count1=0;
    var count2=0;
    var count3=0;
    var count4=0;

    for(var i=0; i<results.length;i++){
        if(results[i].genomic_end_tx-results[i].genomic_start_tx<=0){
            count0=count0+1;
        } else if(results[i].genomic_end_tx-results[i].genomic_start_tx==1){
            count1=count1+1;
        } else if(results[i].genomic_end_tx-results[i].genomic_start_tx==2){
            count2=count2+1;
        } else if(results[i].genomic_end_tx-results[i].genomic_start_tx==3){
            count3=count3+1;
        }
        else if(results[i].genomic_end_tx-results[i].genomic_start_tx==4){
            count4=count4+1;
        }
       
    }

    console.log("exons size 0 or less: "+count0);
    console.log("exons size 1: "+count1);
    console.log("exons size 2: "+count2);
    console.log("exons size 3: "+count3);
    console.log("exons size 4: "+count4);
}

async function runProteinSizeCheck(){
    var results=await sqlQuery("select length,protein_id from proteins");
    var count0=0;
    var count1=0;
    var count2=0;
    var count3=0;
    var count4=0;
    var count5To60=0;

    for(var i=0; i<results.length;i++){
        var calculatedLength=results[i].length;
        if(calculatedLength<=0){
            count0=count0+1;
        } else if(calculatedLength==1){
            count1=count1+1;
        } else if(calculatedLength==2){
            count2=count2+1;
        } else if(calculatedLength==3){
            count3=count3+1;
        }
        else if(calculatedLength==4){
            count4=count4+1;
        }
        else if(calculatedLength>=5 && calculatedLength<=60 ){
            count5To60=count5To60+1;
        }
       
    }

    console.log("protein size 0 or less: "+count0);
    console.log("protein size 1: "+count1);
    console.log("protein size 2: "+count2);
    console.log("protein size 3: "+count3);
    console.log("protein size 4: "+count4);
    console.log("protein size 5 to 60: "+count5To60);
}

async function runSmallSizedDomains(){
    var results=await sqlQuery("select total_length from domainEvent");
    var count0=0;
    var count1=0;
    var count2=0;
    var count3=0;
    var count4=0;

    for(var i=0; i<results.length;i++){
        var calculatedLength=results[i].total_length;
        if(calculatedLength>=0 && calculatedLength<=60){
            count0=count0+1;
        } else if(calculatedLength>60 && calculatedLength<=120){
            count1=count1+1;
        } else if(calculatedLength>120 && calculatedLength<=300){
            count2=count2+1;
        } else if(calculatedLength>300 && calculatedLength<=900){
            count3=count3+1;
        }
        else if(calculatedLength>900){
            count4=count4+1;
        }
      
    }

    console.log("domain size 0 to 60: "+count0);
    console.log("domain size 61 to 120: "+count1);
    console.log("domain size 121 to 300: "+count2);
    console.log("domain size 301 to 900: "+count3);
    console.log("domain size 901+: "+count4);
    console.log("total: "+(count1+count2+count3+count4));

}
