//technical server constructors
var fs = require('fs');
var http = require('http');
var https = require('https');
//var privateKey  = fs.readFileSync('sslcert/server.key', 'utf8');
//var certificate = fs.readFileSync('sslcert/server.crt', 'utf8');
//var credentials = {key: privateKey, cert: certificate};
const express = require("express");
const app = express();
var bodyParser = require('body-parser');
app.use(bodyParser.json());       
app.use(bodyParser.urlencoded({     
    extended: true
}));
var cors = require("cors");
app.use(cors());
app.use(express.json(), function (req, res, next) {
    express.json();
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    next();
});

app.use(express.static('client'));

//querySearch module constructor
const querySearch = require("./querySearch");
app.use('/', querySearch);

//server starts listening to requests
 const port = process.env.PORT || 3000; 
 app.listen(port, () => {
     console.log(`Listening on port ${port}`);

 });
//var httpServer = http.createServer(app);
//var httpsServer = https.createServer(credentials, app);

//httpServer.listen(80);
//httpsServer.listen(443);
//console.log(`Listening on port 80,443`);