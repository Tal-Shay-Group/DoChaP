/*
 * This is the running file that opens the server and get rewuests 
 * for html files and query-searches.  
 */


//technical server constructors
process.env.NODE_ENV = 'production';
var fs = require('fs');
var nodemailer = require('nodemailer');
var transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: 'dochapmail',
      pass: '/*fill in*/'
    }
  });
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

//saving user session ID
var currSessionID=0;

//site files
app.use(express.static('client'));

//mail sender for contact us requests
app.get('/sendMail/:name/:mail/:msg', (req, res) => {
    var mailOptions = {
      from: 'dochapmail@gmail.com',
      to: 'galozs@post.bgu.ac.il', //add on server the e-mail
      subject: 'new Message via DoChaP. From '+req.params.name,
      text: "reply to:\n"+req.params.mail +"\nmessage: \n"+req.params.msg
    };
    transporter.sendMail(mailOptions, function(error, info){});
    fs.writeFile("messages.txt", req.params.name+","+req.params.mail+","+req.params.msg+","+new Date().toLocaleString() + "\r\n", {
        flag: 'a'
    }, function (err) {
    });
    res.status(200).send();
});

//mail sender for contact us requests
app.get('/sendAlert', (req, res) => {
    var today=new Date();
    var lastAlert=new Date();
    if (Math.round((today-lastAlert)/(1000*60*60*24))>90){
        var mailOptions = {
            from: 'dochapmail@gmail.com',
            to: 'galozs@post.bgu.ac.il', //add on server the e-mail
            subject: "DoChaP alert. Update the database",
            text: "The last update was before 90 days."
          };
          
          transporter.sendMail(mailOptions, function(error, info){});
          /*write to files date ... */
    }
    res.status(200).send();
});

//userInterfaceLog
// app.get('/userLog/:msg', (req, res) => {
//     fs.writeFile("userInterfaceLog.txt", req.params.msg+ "\r\n", {
//         flag: 'a'
//     }, function (err) {
//     });
//     res.status(200).send();
// });

//giving session ID 
app.get('/getNewSessionID', (req, res) => {
    currSessionID=currSessionID+1;
    res.status(200).send(""+currSessionID);
});

//querySearch module constructor
const querySearch = require("./querySearch");
app.use('/', querySearch);

//server starts listening to requests
 const port = process.env.PORT || 3000; 
 app.listen(port, () => {
     console.log(`Listening on port ${port}`);

 });