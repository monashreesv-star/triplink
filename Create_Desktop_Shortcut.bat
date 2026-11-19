@echo off
set SCRIPT=%TEMP%\CreateTripLinkShortcut.vbs
if exist "%SCRIPT%" del "%SCRIPT%"
echo Set oWS = WScript.CreateObject("WScript.Shell") >> "%SCRIPT%"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\TripLink.lnk" >> "%SCRIPT%"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%SCRIPT%"
echo oLink.TargetPath = "wscript.exe" >> "%SCRIPT%"
echo oLink.Arguments = """" ^& "%~dp0TripLink_App.vbs" ^& """" >> "%SCRIPT%"
echo oLink.WorkingDirectory = "%~dp0" >> "%SCRIPT%"
echo oLink.Description = "TripLink - Smart Travel Support Platform for TBO" >> "%SCRIPT%"
echo oLink.IconLocation = "shell32.dll,220" >> "%SCRIPT%"
echo oLink.Save >> "%SCRIPT%"
cscript //nologo "%SCRIPT%"
if exist "%SCRIPT%" del "%SCRIPT%"
echo.
echo ==============================================================
echo [SUCCESS] TripLink shortcut created directly on your Desktop!
echo You can now launch TripLink directly from your Desktop.
echo ==============================================================
pause
