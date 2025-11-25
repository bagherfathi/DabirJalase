@echo off
echo Starting Desktop Application...
cd /d %~dp0\desktop-app
echo.
echo Note: Maven is required. If not installed, please install Maven first.
echo.
mvn exec:java -Dexec.mainClass="com.meetingassistant.app.MainApplication"
pause

