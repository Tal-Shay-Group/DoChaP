//technical server constructors
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
