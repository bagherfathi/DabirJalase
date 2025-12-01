# Cross-Platform Setup Guide

## Running Server on Linux and Client on Windows

Yes, you can run the server on Linux and the client on Windows! Here's how:

## Prerequisites

### Linux Server:
- Python 3.12+
- Virtual environment with dependencies installed
- Network access (firewall configured to allow port 8000)

### Windows Client:
- Java 21+ installed
- Maven installed (for building)
- Network access to reach the Linux server

## Setup Instructions

### 1. Linux Server Setup

```bash
# On your Linux machine
cd /path/to/DabirJalase
source python_services/venv/bin/activate  # or activate your venv
python3 -m python_services
```

**Important:** The server binds to `0.0.0.0:8000` by default, which means it accepts connections from any network interface.

**To allow remote connections:**
- Make sure port 8000 is open in your firewall:
  ```bash
  # Ubuntu/Debian
  sudo ufw allow 8000/tcp
  
  # Or if using iptables
  sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
  ```

- Find your Linux server's IP address:
  ```bash
  # Get IP address
  hostname -I
  # or
  ip addr show
  # or
  ifconfig
  ```

### 2. Windows Client Setup

**Option A: Using Environment Variable**
```cmd
# Set environment variable before running
set MEETING_ASSISTANT_SERVER_URL=http://YOUR_LINUX_IP:8000
mvn exec:java -Dexec.mainClass="com.meetingassistant.app.MainApplication"
```

**Option B: Using System Property**
```cmd
mvn exec:java -Dexec.mainClass="com.meetingassistant.app.MainApplication" -Dmeeting.assistant.server.url=http://YOUR_LINUX_IP:8000
```

**Option C: Build JAR and run with environment variable**
```cmd
# Build the JAR
mvn clean package

# Run with environment variable
set MEETING_ASSISTANT_SERVER_URL=http://YOUR_LINUX_IP:8000
java -jar target/desktop-app-0.1.0-SNAPSHOT.jar
```

### 3. Configuration Priority

The client will use the server URL in this order:
1. Environment variable: `MEETING_ASSISTANT_SERVER_URL`
2. System property: `meeting.assistant.server.url`
3. Default: `http://localhost:8000`

## Testing Connection

### From Windows Client:
```cmd
# Test if you can reach the server
curl http://YOUR_LINUX_IP:8000/health
# Should return: {"status":"ok","message":"scaffold"}
```

### From Linux Server:
```bash
# Check if server is listening on all interfaces
netstat -tlnp | grep 8000
# Should show: 0.0.0.0:8000 (not just 127.0.0.1:8000)
```

## Troubleshooting

### Connection Refused
- Check firewall on Linux server
- Verify server is running: `curl http://localhost:8000/health` on Linux
- Check if server binds to `0.0.0.0` (not just `127.0.0.1`)

### Can't Reach Server
- Verify network connectivity: `ping YOUR_LINUX_IP` from Windows
- Check if port 8000 is accessible: `telnet YOUR_LINUX_IP 8000` from Windows
- Verify server IP address is correct

### CORS Issues
- The server should handle CORS automatically, but if you see CORS errors, check the server's `allowed_origins` configuration

## Security Considerations

For production:
1. Use HTTPS instead of HTTP
2. Set up authentication (API key)
3. Use a reverse proxy (nginx) for better security
4. Restrict firewall rules to specific IP addresses if possible

## Example Configuration

**Linux Server (192.168.1.100):**
```bash
export PY_SERVICES_HOST=0.0.0.0
export PY_SERVICES_PORT=8000
python3 -m python_services
```

**Windows Client:**
```cmd
set MEETING_ASSISTANT_SERVER_URL=http://192.168.1.100:8000
mvn exec:java -Dexec.mainClass="com.meetingassistant.app.MainApplication"
```

The client will automatically connect to the Linux server at startup!

