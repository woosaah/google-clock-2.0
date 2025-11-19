# MCP Server for Google Clock 2.0

The Model Context Protocol (MCP) server allows AI tools (like Claude Desktop) to query the Google Clock 2.0 application state, settings, and data.

## Features

The MCP server exposes the following tools:

### Application Status
- `get_application_status` - Get overall system health and statistics

### Settings
- `get_settings` - Get current application settings (all or specific key)

### API Integrations
- `get_api_integrations` - List all connected external APIs
- Query which APIs are enabled
- View last run times and error counts

### Automation Rules
- `get_response_rules` - Get configured automation rules
- Filter by enabled status
- View trigger counts and last execution times

### Person Detection
- `get_recent_detections` - Get recent face detections
- `get_known_persons` - List persons with trained face models
- View detection confidence and greeting status

### Media
- `get_media_queue` - Get current playback queue
- `get_media_library_stats` - Statistics about local media
- `search_media` - Search media library by filename

### Voice Assistant
- `get_voice_command_history` - Recent voice commands and responses

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Claude Desktop (or other MCP client)

Add to your Claude Desktop configuration (usually `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "google-clock": {
      "command": "python",
      "args": ["/path/to/google-clock-2.0/backend/mcp_server.py"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@192.168.1.243/googleclock"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

After adding the configuration, restart Claude Desktop. The MCP server will start automatically when Claude Desktop launches.

## Usage Examples

Once configured, you can ask Claude questions about your Google Clock system:

**Query Application Status:**
```
What's the status of my Google Clock system?
```

**View Connected APIs:**
```
Show me all connected API integrations
```

**Check Person Detections:**
```
Who has been detected by the face recognition system today?
```

**Search Media:**
```
Find all videos with "family" in the filename
```

**View Automation Rules:**
```
List all active automation rules
```

**Check Voice Command History:**
```
What voice commands were processed in the last hour?
```

## Available Tools

### `get_application_status`
Returns overall system health and statistics.

**Parameters:** None

**Example Response:**
```json
{
  "service": "Google Clock 2.0",
  "version": "2.0.0",
  "timestamp": "2024-01-01T12:00:00",
  "components": {
    "backend": "running",
    "database": "connected"
  },
  "statistics": {
    "total_settings": 5,
    "total_api_integrations": 3,
    "total_rules": 7,
    "total_persons": 2,
    "total_detections": 45,
    "media_queue_size": 0
  }
}
```

### `get_settings`
Get application settings.

**Parameters:**
- `key` (optional): Specific setting key

**Example:**
```json
{
  "key": "clock_format"
}
```

### `get_api_integrations`
List all API integrations.

**Parameters:**
- `enabled_only` (boolean, default: false): Return only enabled integrations

**Example Response:**
```json
[
  {
    "id": 1,
    "name": "OpenWeatherMap",
    "url": "https://api.openweathermap.org/data/2.5/weather",
    "method": "GET",
    "enabled": true,
    "last_run": "2024-01-01T11:55:00",
    "next_run": "2024-01-01T12:05:00",
    "error_count": 0,
    "schedule_interval": 600
  }
]
```

### `get_response_rules`
Get automation rules.

**Parameters:**
- `enabled_only` (boolean, default: false): Return only enabled rules

### `get_recent_detections`
Get recent person detections.

**Parameters:**
- `hours` (number, default: 24): Hours to look back
- `limit` (number, default: 50): Maximum results

**Example Response:**
```json
[
  {
    "id": 123,
    "person_id": 1,
    "person_name": "Cole",
    "detected_at": "2024-01-01T11:30:00",
    "confidence": 0.92,
    "first_of_day": true,
    "greeted": true
  }
]
```

### `get_known_persons`
List persons with trained face models.

**Example Response:**
```json
[
  {
    "id": 1,
    "name": "Cole",
    "has_face_encoding": true,
    "photo_samples": 5,
    "greetings": {
      "morning": "Good morning, Cole!",
      "afternoon": "Hey Cole!",
      "evening": "Good evening, Cole!"
    }
  }
]
```

### `get_media_queue`
Get current media queue.

**Parameters:**
- `status` (optional): Filter by status (queued, playing, played, error)

### `get_media_library_stats`
Get media library statistics.

**Example Response:**
```json
{
  "total_files": 150,
  "by_type": {
    "video": 45,
    "audio": 80,
    "photo": 25
  },
  "total_size_bytes": 52428800000,
  "most_played": [...]
}
```

### `get_voice_command_history`
Get recent voice commands.

**Parameters:**
- `hours` (number, default: 24): Hours to look back
- `limit` (number, default: 20): Maximum results

### `search_media`
Search media library.

**Parameters:**
- `query` (required): Search query for filename
- `media_type` (optional): Filter by type (video, audio, photo)

## Troubleshooting

### MCP Server Not Appearing in Claude Desktop

1. Check the configuration file path
2. Verify the Python path is correct
3. Ensure DATABASE_URL environment variable is set
4. Check Claude Desktop logs: `~/Library/Logs/Claude/`

### Database Connection Errors

Ensure the DATABASE_URL in the MCP configuration matches your backend .env file:

```bash
# Check backend .env
cat /path/to/google-clock-2.0/backend/.env | grep DATABASE_URL
```

### Permission Errors

Make sure the mcp_server.py file is executable:

```bash
chmod +x /path/to/google-clock-2.0/backend/mcp_server.py
```

## Development

### Testing the MCP Server

You can test the MCP server manually using stdio:

```bash
cd backend
python mcp_server.py
```

Then send JSON-RPC requests:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

### Adding New Tools

To add a new tool:

1. Add the tool definition in `list_tools()`
2. Add the handler in `call_tool()`
3. Implement the tool function
4. Update this README with documentation

## Security Considerations

- The MCP server has full database access
- Only use with trusted MCP clients
- Do not expose the MCP server over a network
- The server runs locally and communicates via stdio only

## References

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://modelcontextprotocol.io/clients/claude-desktop)
