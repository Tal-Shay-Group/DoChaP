@echo off
REM Run this script from the DoChaP-web project root (same folder as app.js).
REM Downloads all third-party JS/CSS libraries into client\lib\ so the app
REM works without depending on external CDNs.

setlocal

set LIB=client\lib

REM Always fetch through :fetch. Plain `curl -L -o` exits 0 on an HTTP error
REM and writes the error body to the target file, so a CDN hiccup silently
REM installs a 404 page named jquery.min.js. -f makes curl fail on 4xx/5xx,
REM and the bad file is deleted rather than left in place. client\lib\ is
REM gitignored and refetched on every deploy, so it would otherwise ship
REM straight to users.
goto :main

:fetch
curl -fL --retry 3 --retry-delay 2 --connect-timeout 20 -o %1 %2
if errorlevel 1 (
    del %1 2>nul
    echo ERROR: failed to download %2 1>&2
    exit /b 1
)
exit /b 0

:main
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
call :fetch "%LIB%\bootstrap\css\bootstrap.min.css" "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css"
if errorlevel 1 exit /b 1
call :fetch "%LIB%\bootstrap\js\bootstrap.min.js" "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"
if errorlevel 1 exit /b 1

echo.
echo Downloading Bootstrap glyphicon fonts...
call :fetch "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.eot"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.eot"
if errorlevel 1 exit /b 1
call :fetch "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.svg"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.svg"
if errorlevel 1 exit /b 1
call :fetch "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.ttf"   "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.ttf"
if errorlevel 1 exit /b 1
call :fetch "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.woff"  "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.woff"
if errorlevel 1 exit /b 1
call :fetch "%LIB%\bootstrap\fonts\glyphicons-halflings-regular.woff2" "https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/fonts/glyphicons-halflings-regular.woff2"
if errorlevel 1 exit /b 1

echo.
echo Downloading jQuery 3.5.1...
call :fetch "%LIB%\jquery\jquery.min.js" "https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js"
if errorlevel 1 exit /b 1

echo.
echo Downloading AngularJS 1.7.8 (core, route, animate)...
call :fetch "%LIB%\angular\angular.js"         "https://ajax.googleapis.com/ajax/libs/angularjs/1.7.8/angular.js"
if errorlevel 1 exit /b 1
call :fetch "%LIB%\angular\angular-route.js"   "https://code.angularjs.org/1.7.8/angular-route.js"
if errorlevel 1 exit /b 1
call :fetch "%LIB%\angular\angular-animate.js" "https://code.angularjs.org/1.7.8/angular-animate.js"
if errorlevel 1 exit /b 1

echo.
echo Downloading ion-rangeslider 2.3.1...
call :fetch "%LIB%\ion-rangeslider\ion.rangeSlider.min.css" "https://cdnjs.cloudflare.com/ajax/libs/ion-rangeslider/2.3.1/css/ion.rangeSlider.min.css"
if errorlevel 1 exit /b 1
call :fetch "%LIB%\ion-rangeslider\ion.rangeSlider.min.js"  "https://cdnjs.cloudflare.com/ajax/libs/ion-rangeslider/2.3.1/js/ion.rangeSlider.min.js"
if errorlevel 1 exit /b 1

echo.
echo Downloading jsPDF 1.5.3...
call :fetch "%LIB%\jspdf\jspdf.debug.js" "https://cdnjs.cloudflare.com/ajax/libs/jspdf/1.5.3/jspdf.debug.js"
if errorlevel 1 exit /b 1

echo.
echo Done. All vendor libraries placed under %LIB%\
endlocal
