# PowerShell script to run desktop app with remote server
$env:MEETING_ASSISTANT_SERVER_URL = "http://10.211.1.24:8000"

Write-Host "Starting Desktop Application..." -ForegroundColor Green
Write-Host "Server URL: $env:MEETING_ASSISTANT_SERVER_URL" -ForegroundColor Cyan
Write-Host ""

cd desktop-app

# Find Maven
$mvnCmd = $null
if ($env:MAVEN) {
    $mvnCmd = Join-Path $env:MAVEN "mvn.cmd"
} elseif ($env:MAVEN_HOME) {
    $mvnCmd = Join-Path $env:MAVEN_HOME "bin\mvn.cmd"
} else {
    # Try common locations
    $commonPaths = @(
        "D:\maven\bin\mvn.cmd",
        "$env:ProgramFiles\Apache\maven\bin\mvn.cmd",
        "$env:ProgramFiles(x86)\Apache\maven\bin\mvn.cmd"
    )
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            $mvnCmd = $path
            break
        }
    }
}

if ($mvnCmd -and (Test-Path $mvnCmd)) {
    Write-Host "Using Maven: $mvnCmd" -ForegroundColor Yellow
    Write-Host ""
    & $mvnCmd exec:java -Dexec.mainClass="com.meetingassistant.app.MainApplication"
} else {
    Write-Host "Maven not found. Trying to run from JAR..." -ForegroundColor Yellow
    if (Test-Path "target/desktop-app-0.1.0-SNAPSHOT.jar") {
        java -jar target/desktop-app-0.1.0-SNAPSHOT.jar
    } else {
        Write-Host "JAR file not found. Please install Maven and build the project:" -ForegroundColor Red
        Write-Host "  mvn clean package" -ForegroundColor Yellow
    }
}

