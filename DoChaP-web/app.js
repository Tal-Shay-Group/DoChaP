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
// Large limit so the DOMAS page can upload input files (base64) in the JSON body.
app.use(bodyParser.json({ limit: '100mb' }));
app.use(bodyParser.urlencoded({
    extended: true,
    limit: '100mb'
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

// Contact-form fields arrive as URL path segments, so they are entirely
// attacker-controlled. Validate before they reach a mail header or the log
// file: a CR/LF in the name or address is the classic way to inject extra
// mail headers, and an unescaped comma or newline forges fields and records
// in messages.txt.
var MAX_NAME = 100;
var MAX_MAIL = 254;  // RFC 5321 maximum address length
var MAX_MSG = 5000;
var EMAIL_RE = /^[^\s@,;:<>"()\[\]\\]+@[^\s@,;:<>"()\[\]\\]+\.[A-Za-z]{2,}$/;

// Returns an error string, or null when the submission is acceptable.
function validateContact(name, mail, msg) {
    if (!name || !mail || !msg) {
        return "name, e-mail and message are all required";
    }
    if (/[\r\n]/.test(name) || /[\r\n]/.test(mail)) {
        return "line breaks are not allowed in the name or e-mail address";
    }
    if (name.length > MAX_NAME) {
        return "name is longer than " + MAX_NAME + " characters";
    }
    if (mail.length > MAX_MAIL) {
        return "e-mail address is longer than " + MAX_MAIL + " characters";
    }
    if (msg.length > MAX_MSG) {
        return "message is longer than " + MAX_MSG + " characters";
    }
    if (!EMAIL_RE.test(mail)) {
        return "e-mail address is not valid";
    }
    return null;
}

// Quote one field of the messages.txt line so a comma, quote or newline in
// the input cannot forge extra columns or extra rows. Note the timestamp
// needs this too - toLocaleString() itself contains a comma.
function csvField(value) {
    return '"' + String(value).replace(/"/g, '""') + '"';
}

//mail sender for contact us requests
app.get('/sendMail/:name/:mail/:msg', (req, res) => {
    var name = req.params.name.trim();
    var mail = req.params.mail.trim();
    var msg = req.params.msg.trim();

    var invalid = validateContact(name, mail, msg);
    if (invalid) {
        res.status(400).send(invalid);
        return;
    }

    var mailOptions = {
      from: 'dochapmail@gmail.com',
      to: 'galozs@post.bgu.ac.il', //add on server the e-mail
      subject: 'new Message via DoChaP. From '+name,
      text: "reply to:\n"+mail +"\nmessage: \n"+msg
    };
    transporter.sendMail(mailOptions, function(error, info){});
    var logLine = [csvField(name), csvField(mail), csvField(msg),
                   csvField(new Date().toLocaleString())].join(",");
    fs.writeFile("messages.txt", logLine + "\r\n", {
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

//DOMAS module: runs domas.py on uploaded splicing-tool output
const domas = require("./domas");
app.use('/', domas);

//server starts listening to requests
 const port = process.env.PORT || 3000; 
 app.listen(port, () => {
     console.log(`Listening on port ${port}`);

 });