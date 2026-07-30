#!/bin/bash
# Run this script from the DoChaP-web project root (same folder as app.js).
# Downloads all third-party JS/CSS libraries into client/lib/ so the app
# works without depending on external CDNs.

set -e

LIB="client/lib"

# Always fetch through this helper. Plain `curl -L -o` exits 0 on an HTTP
# error and writes the error body to the target file, so `set -e` does not
# fire and a CDN hiccup silently installs a 404 page named jquery.min.js.
# -f makes curl fail on 4xx/5xx, and the file is removed rather than left
# truncated. client/lib/ is gitignored and refetched on every deploy, so a
# bad download would otherwise ship straight to users.
fetch() {
    local dest="$1" url="$2"
    curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -o "$dest" "$url" || {
        rm -f "$dest"
        echo "ERROR: failed to download $url" >&2
        return 1
    }
    if [ ! -s "$dest" ]; then
        rm -f "$dest"
        echo "ERROR: downloaded an empty file from $url" >&2
        return 1
    fi
}

echo "Creating directory structure..."
mkdir -p "$LIB/bootstrap/css"
mkdir -p "$LIB/bootstrap/js"
mkdir -p "$LIB/bootstrap/fonts"
mkdir -p "$LIB/jquery"
mkdir -p "$LIB/angular"
mkdir -p "$LIB/ion-rangeslider"
mkdir -p "$LIB/jspdf"

echo
echo "Downloading Bootstrap 3.4.1..."
fetch "$LIB/bootstrap/css/bootstrap.min.css" "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css"
fetch "$LIB/bootstrap/js/bootstrap.min.js"  "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"

echo
echo "Downloading Bootstrap glyphicon fonts..."
fetch "$LIB/bootstrap/fonts/glyphicons-halflings-regular.eot"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.eot"
fetch "$LIB/bootstrap/fonts/glyphicons-halflings-regular.svg"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.svg"
fetch "$LIB/bootstrap/fonts/glyphicons-halflings-regular.ttf"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.ttf"
fetch "$LIB/bootstrap/fonts/glyphicons-halflings-regular.woff"  "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.woff"
fetch "$LIB/bootstrap/fonts/glyphicons-halflings-regular.woff2" "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.woff2"

echo
echo "Downloading jQuery 3.5.1..."
fetch "$LIB/jquery/jquery.min.js" "https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"

echo
echo "Downloading AngularJS 1.7.8 (core, route, animate)..."
fetch "$LIB/angular/angular.js"         "https://ajax.googleapis.com/ajax/libs/angularjs/1.7.8/angular.js"
fetch "$LIB/angular/angular-route.js"   "https://code.angularjs.org/1.7.8/angular-route.js"
fetch "$LIB/angular/angular-animate.js" "https://code.angularjs.org/1.7.8/angular-animate.js"

echo
echo "Downloading ion-rangeslider 2.3.1..."
fetch "$LIB/ion-rangeslider/ion.rangeSlider.min.css" "https://cdnjs.cloudflare.com/ajax/libs/ion-rangeslider/2.3.1/css/ion.rangeSlider.min.css"
fetch "$LIB/ion-rangeslider/ion.rangeSlider.min.js"  "https://cdnjs.cloudflare.com/ajax/libs/ion-rangeslider/2.3.1/js/ion.rangeSlider.min.js"

echo
echo "Downloading jsPDF 1.5.3..."
fetch "$LIB/jspdf/jspdf.debug.js" "https://cdnjs.cloudflare.com/ajax/libs/jspdf/1.5.3/jspdf.debug.js"

echo
echo "Done. All vendor libraries placed under $LIB/"
