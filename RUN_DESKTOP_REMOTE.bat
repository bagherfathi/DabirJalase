@echo off
echo ========================================
echo Starting Desktop Application
echo Configuration will be loaded from config.properties
echo (or environment variables/system properties)
echo ========================================
echo.

cd /d %~dp0\desktop-app

REM Optional: Override config file with environment variable
REM set MEETING_ASSISTANT_SERVER_URL=http://10.211.1.24:8000

REM Try to use Maven from common locations
if exist "D:\maven\bin\mvn.cmd" (
    echo Using Maven: D:\maven\bin\mvn.cmd
    echo Compiling and running application...
    echo Server URL: %MEETING_ASSISTANT_SERVER_URL%
    echo.
    REM Pass both as environment variable and system property for maximum compatibility
    D:\maven\bin\mvn.cmd clean compile exec:java "-Dexec.mainClass=com.meetingassistant.app.MainApplication" "-Dexec.systemProperties=meeting.assistant.server.url=%MEETING_ASSISTANT_SERVER_URL%"
) else if exist "%MAVEN%\mvn.cmd" (
    echo Using Maven: %MAVEN%\mvn.cmd
    echo Compiling and running application...
    echo Server URL: %MEETING_ASSISTANT_SERVER_URL%
    echo.
    REM Pass both as environment variable and system property for maximum compatibility
    %MAVEN%\mvn.cmd clean compile exec:java "-Dexec.mainClass=com.meetingassistant.app.MainApplication" "-Dexec.systemProperties=meeting.assistant.server.url=%MEETING_ASSISTANT_SERVER_URL%"
) else (
    echo Maven not found. Please install Maven or update the path in this script.
    pause
    exit /b 1
)

pause

