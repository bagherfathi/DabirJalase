# How to Run Desktop App on Windows

## Method 1: Using Batch File (Easiest)

Simply double-click or run:
```cmd
RUN_DESKTOP_REMOTE.bat
```

This will:
- Set the server URL to `http://10.211.1.24:8000`
- Compile the project
- Run the application

## Method 2: Manual Command Line

### Step 1: Open Command Prompt or PowerShell

Navigate to the project root directory:
```cmd
cd D:\meta\projects\speech\DabirJalase
```

### Step 2: Set Environment Variable

Set the server URL:
```cmd
set MEETING_ASSISTANT_SERVER_URL=http://10.211.1.24:8000
```

Or in PowerShell:
```powershell
$env:MEETING_ASSISTANT_SERVER_URL="http://10.211.1.24:8000"
```

### Step 3: Navigate to desktop-app directory

```cmd
cd desktop-app
```

### Step 4: Run with Maven

**In Command Prompt (CMD):**
```cmd
mvn clean compile exec:java -Dexec.mainClass=com.meetingassistant.app.MainApplication
```

Or with full path:
```cmd
D:\maven\bin\mvn.cmd clean compile exec:java -Dexec.mainClass=com.meetingassistant.app.MainApplication
```

**In PowerShell (IMPORTANT - use quotes):**
```powershell
& "D:\maven\bin\mvn.cmd" clean compile exec:java "-Dexec.mainClass=com.meetingassistant.app.MainApplication"
```

Or if Maven is in PATH:
```powershell
mvn clean compile exec:java "-Dexec.mainClass=com.meetingassistant.app.MainApplication"
```

**Note:** In PowerShell, you must quote the `-Dexec.mainClass=...` argument, otherwise PowerShell will split it incorrectly.

## Method 3: Using System Property Instead of Environment Variable

**In Command Prompt:**
```cmd
cd desktop-app
mvn exec:java -Dexec.mainClass=com.meetingassistant.app.MainApplication -Dmeeting.assistant.server.url=http://10.211.1.24:8000
```

**In PowerShell (use quotes):**
```powershell
cd desktop-app
mvn exec:java "-Dexec.mainClass=com.meetingassistant.app.MainApplication" "-Dmeeting.assistant.server.url=http://10.211.1.24:8000"
```

## Method 4: Run from Pre-built JAR (if available)

First build the JAR:
```cmd
cd desktop-app
mvn clean package
```

Then run:
```cmd
set MEETING_ASSISTANT_SERVER_URL=http://10.211.1.24:8000
java -jar target/desktop-app-0.1.0-SNAPSHOT.jar
```

## Configuration Priority

The application reads the server URL in this order:
1. Environment variable: `MEETING_ASSISTANT_SERVER_URL`
2. System property: `meeting.assistant.server.url`
3. Default: `http://localhost:8000`

## Troubleshooting

### Maven not found
- Install Maven from https://maven.apache.org/
- Or add Maven to your PATH environment variable
- Or update the path in `RUN_DESKTOP_REMOTE.bat`

### Java not found
- Ensure Java 21+ is installed
- Add Java to your PATH environment variable

### Application window doesn't appear
- Wait a few seconds (JavaFX may take time to initialize)
- Check taskbar or use Alt+Tab
- Check console for error messages

