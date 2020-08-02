DoChaP is a full-stack architecture website. The server code is written in NodeJS and shown in &quot;dochap-web&quot; and it delivers client-side files (written in AngularJS) from the &quot;client&quot; folder.

**Server-Side**

The runnable file in the server is app.js that uses querySearch.js for the querying the database and QueryCache.js for caching results and delivering them faster.

validateDatabase.js is for inner use to look for bugs in database data.

**Client-Side**

Client files are divided into 4 folders: modules, pages, resources and services, as explained below. Besides these, index.html is the main file and is sent with the connected files: main.css, indexController.js, app.js.

GraphicUtils.js contains helper functions that may be used by different modules or pages.

**modules:** All of the biologic logic are is these files. Also, graphic calculations can be found there. Sorted using OOP objects.

**pages:** HTML resources and their JavaScript controllers are located there. Sorted by matching folders.

**resources:** This folder contains pictures and non-code files.

**services:** This folder contains files that can be used by different pages to query the server. webServices.js is a file with actual http requests according to the server API.

In addition, there is documentation in each file.

**Running Code Locally**

1. Download Git and Node (if you don&#39;t already have them).
2. Open a folder to locate the code there.
3. Open cmd in the location of this folder and write:
git init
After finishing write:
git pull [https://github.com/Tal-Shay-Group/DoChaP](https://github.com/Tal-Shay-Group/DoChaP)
4. Go to the folder dochap-web and run cmd from this folder and write:
npm i
5. Download the updated database file and put inside the folder dochap-web.
6. Open cmd in the dochap-web folder and write:
node app.js
7. go to the web browser (Google Chrome recommended) and type the url: localhost:3000
8. The site should now work.
9. To close the site you must go to the cmd window and press ctrl+c to shut it down. You can exit the browser normally.

