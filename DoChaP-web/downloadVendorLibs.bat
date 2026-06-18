@echo off
REM Run this script from the DoChaP-web project root (same folder as app.js).
REM Downloads all third-party JS/CSS libraries into client\lib\ so the app
REM works without depending on external CDNs.

setlocal

set LIB=client\lib

echo Creating directory structure...
mkdir "%LIB%\bootstrap\css" 2>nul
mkdir "%LIB%\bootstrap\js" 2>nul
mkdir "%LIB%\bootstrap\fonts" 2>nul
mkdir "%LIB%\jquery" 2>nul
mkdir "%LIB%\angular" 2>nul
mkdir "%LIB%\ion-rangeslider" 2>nul
mkdir "%LIB%\jspdf" 2>nul

echo.
echo Downloading Bootstrap 3.4.1...
curl -L -o "%LIB%\bootstrap\css\bootstrap.min.css" "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css"
curl -L -o "%LIB%\bootstrap\js\bootstrap.min.js" "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"

echo.
echo Downloading Bootstrap glyphicon fonts...
curl -L -o "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.eot"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.eot"
curl -L -o "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.svg"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.svg"
curl -L -o "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.ttf"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.ttf"
curl -L -o "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.woff"  "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.woff"
curl -L -o "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.woff2" "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.woff2"

echo.
echo Downloading jQuery 3.4.1...
curl -L -o "%LIB%\jquery\jquery.min.js" "https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js"

echo.
echo Downloading AngularJS 1.7.8 (core, route, animate)...
curl -L -o "%LIB%\angular\angular.js"         "https://ajax.googleapis.com/ajax/libs/angularjs/1.7.8/angular.js"
curl -L -o "%LIB%\angular\angular-route.js"   "https://code.angularjs.org/1.7.8/angular-route.js"
curl -L -o "%LIB%\angular\angular-animate.js" "https://code.angularjs.org/1.7.8/angular-animate.js"

echo.
echo Downloading ion-rangeslider 2.3.1...
curl -L -o "%LIB%\ion-rangeslider\ion.rangeSlider.min.css" "https://cdnjs.cloudflare.com/ajax/libs/ion-rangeslider/2.3.1/css/ion.rangeSlider.min.css"
curl -L -o "%LIB%\ion-rangeslider\ion.rangeSlider.min.js"  "https://cdnjs.cloudflare.com/ajax/libs/ion-rangeslider/2.3.1/js/ion.rangeSlider.min.js"

echo.
echo Downloading jsPDF 1.5.3...
curl -L -o "%LIB%\jspdf\jspdf.debug.js" "https://cdnjs.cloudflare.com/ajax/libs/jspdf/1.5.3/jspdf.debug.js"

echo.
echo Done. All vendor libraries placed under %LIB%\
endlocal
