const sqlite3 = require('sqlite3').verbose();
 
// open the database
const path = require('path')
const dbPath = path.resolve(__dirname, 'DB_merged.sqlite')
const db = new sqlite3.Database(dbPath)
exports.db = db;