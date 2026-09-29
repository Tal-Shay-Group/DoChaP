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

1. Download Git and Node (if you don&#39;t already have them). Current version was tested on node v22.22.2.
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


**Publishing the database**

The download page offers `DB_merged.sqlite`, the same database the server queries,
as a gzip-compressed tar archive of about 933 MB (3.9 GB unpacked). It is hosted as a
**GitHub release asset** on the DOMAS repository, not served from this host:

<https://github.com/Tal-Shay-Group/DOMAS/releases/tag/db-v1>

The `db-v1` asset is 978,165,954 bytes, sha256
`f16675ec6bfcfbe906a36251058095bff27886e43e83db251d1ff032f08146bc`.

Serving it from here was tried and does not work. The network path in front of this
server truncates every HTTPS response at about 27 MB - measured at 27,672,698 to
27,680,698 bytes across three runs on two different client networks, with transfer
times from 11 s to 38 s, so it is a size cap and not a timeout. Requests carrying a
`Range:` header are dropped before any reply arrives. The same requests over loopback
on the server itself return the full 978,095,100 bytes in about 6 s and answer ranged
requests with `206`, so neither Apache nor the file is at fault. Until that cap is
lifted, any link pointing at this host will fail part way through for every user, and
the download page therefore does not offer one.

To publish a rebuilt database:

1. Build the archive beside the database (about a minute). Note that `tar -czf`
   produces a **tar** archive, so the file must be named `.tar.gz` and unpacked with
   `tar -xzf`, not `gunzip`:

   ```
   cd <the folder holding app.js>
   tar -czf DB_merged.sqlite.tar.gz DB_merged.sqlite
   ```

2. Record its checksum, and publish that alongside the file so readers can verify a
   1 GB download that may have been interrupted:

   ```
   sha256sum DB_merged.sqlite.tar.gz          # Linux, macOS
   certutil -hashfile DB_merged.sqlite.tar.gz SHA256   # Windows
   ```

3. Attach it to a GitHub release on the DOMAS repository, either by dragging it onto
   a new release in the web UI or with the `gh` CLI:

   ```
   gh release create db-v1 DB_merged.sqlite.tar.gz \
      --repo Tal-Shay-Group/DOMAS \
      --title "DoChaP database" \
      --notes "SQLite database built 17 September 2026. sha256: <checksum>"
   ```

   The per-file limit for release assets is 2 GiB, and assets are served from a CDN
   that supports resuming, so an interrupted download continues rather than restarting.

4. Update the link and the stated size in
   `client/pages/downloads/downloads.html`, and in the DOMAS `README.md`.

The database deliberately is not served by this node app either: every byte would
cross the node event loop and then the reverse proxy in front of it, competing with
DOMAS runs for the same single-threaded process. `app.js` serves only `client/`, and
the database sits a level above it, so it is not web-reachable by accident.
