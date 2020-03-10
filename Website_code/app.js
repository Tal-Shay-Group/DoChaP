/*
 * This is the running file that opens the server and get rewuests 
 * for html files and query-searches.  
 */


//technical server constructors
var fs = require('fs');
var http = require('http');
var https = require('https');
//var nodemailer = require('nodemailer');
// var transporter = nodemailer.createTransport({
//     service: 'gmail',
//     auth: {
//       user: 'youremail@gmail.com',
//       pass: 'yourpassword'
//     }
//   });
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

//site files
app.use(express.static('client'));

//mail sender for contact us requests
app.get('/sendMail/:name/:mail/:msg', (req, res) => {
    var mailOptions = {
      from: '',
      to: '', //add on server the e-mail
      subject: 'new Message via DoChaP Contact Us.',
      text: "reply to: "+req.params.mail +"\nmessage: \n"+req.params.msg
    };
    
    transporter.sendMail(mailOptions, function(error, info){ });
    res.status(200).send();
});

//userInterfaceLog
app.get('/userLog/:msg', (req, res) => {
    now=new Date();
    fs.writeFile("userInterfaceLog.txt", req.params.msg+","+now + "\n", {
        flag: 'a'
    }, function (err) {});
    res.status(200).send();
});

//querySearch module constructor
const querySearch = require("./querySearch");
app.use('/', querySearch);

//server starts listening to requests
 const port = process.env.PORT || 3000; 
 app.listen(port, () => {
     console.log(`Listening on port ${port}`);

 });