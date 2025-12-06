# Configuration Guide

The desktop application uses a configuration file to manage settings. This makes it easy to change server URLs, API keys, and other settings without modifying code or environment variables.

## Configuration File Location

The application looks for `config.properties` in the following locations (in order of priority):

1. **Current directory**: `./config.properties`
2. **User home directory**: `~/.meetingassistant/config.properties`
3. **Resources**: `src/main/resources/config.properties` (bundled with the app)

## Configuration Priority

Settings are loaded in this order (later sources override earlier ones):

1. Default values (hardcoded)
2. `config.properties` file
3. Environment variables
4. System properties (highest priority)

## Configuration Properties

### Server Configuration

```properties
# Server URL (required)
server.url=http://10.211.1.24:8000

# API Key (optional, leave empty if not required)
api.key=
```

### Connection Settings

```properties
# Connection timeout in milliseconds (default: 5000)
connection.timeout=5000

# Read timeout in milliseconds (default: 10000)
read.timeout=10000
```

### Audio Settings

```properties
# Default language for sessions (default: fa)
default.language=fa
```

### UI Settings

```properties
# Window width (default: 900)
window.width=900

# Window height (default: 700)
window.height=700
```

## Example Configuration File

Create a `config.properties` file in the project root or your home directory:

```properties
# Meeting Assistant Desktop App Configuration

# Server Configuration
server.url=http://10.211.1.24:8000
api.key=

# Connection Settings
connection.timeout=5000
read.timeout=10000

# Audio Settings
default.language=fa

# UI Settings
window.width=900
window.height=700
```

## Overriding with Environment Variables

You can still override settings using environment variables:

```bash
# Windows (CMD)
set MEETING_ASSISTANT_SERVER_URL=http://192.168.1.100:8000

# Windows (PowerShell)
$env:MEETING_ASSISTANT_SERVER_URL="http://192.168.1.100:8000"

# Linux/Mac
export MEETING_ASSISTANT_SERVER_URL=http://192.168.1.100:8000
```

## Overriding with System Properties

You can also override using Java system properties:

```bash
java -Dmeeting.assistant.server.url=http://192.168.1.100:8000 -jar app.jar
```

Or with Maven:

```bash
mvn exec:java -Dexec.mainClass=com.meetingassistant.app.MainApplication -Dmeeting.assistant.server.url=http://192.168.1.100:8000
```

## Default Values

If no configuration is found, the application uses these defaults:

- `server.url`: `http://localhost:8000`
- `api.key`: `null` (not set)
- `connection.timeout`: `5000` ms
- `read.timeout`: `10000` ms
- `default.language`: `fa`
- `window.width`: `900`
- `window.height`: `700`

## Troubleshooting

### Configuration Not Loading

Check the console output when starting the app. You should see:
```
[INFO] Loaded configuration from: /path/to/config.properties
[INFO] Current configuration:
  server.url: http://10.211.1.24:8000
  ...
```

### Configuration Override Not Working

Remember the priority order:
1. System properties (highest)
2. Environment variables
3. Config file
4. Defaults (lowest)

If you set an environment variable but it's not being used, check if a system property is overriding it.

