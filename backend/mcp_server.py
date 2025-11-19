#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for Google Clock 2.0
Allows AI tools to query application state, settings, APIs, and more.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel
from sqlalchemy import func

from app.database import (
    SessionLocal,
    Settings as SettingsModel,
    APIIntegration,
    ResponseRule,
    Detection,
    Person,
    MediaQueue,
    VoiceCommand,
    MediaLibrary,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Server instance
server = Server("google-clock-2.0")


# Helper function to get database session
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


# Tool: Get application status
@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="get_application_status",
            description="Get overall application status and health information",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_settings",
            description="Get current application settings",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Specific setting key (optional, returns all if not specified)",
                    }
                },
            },
        ),
        Tool(
            name="get_api_integrations",
            description="Get all connected API integrations",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled_only": {
                        "type": "boolean",
                        "description": "Return only enabled integrations",
                        "default": False,
                    }
                },
            },
        ),
        Tool(
            name="get_response_rules",
            description="Get automation rules configured in the system",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled_only": {
                        "type": "boolean",
                        "description": "Return only enabled rules",
                        "default": False,
                    }
                },
            },
        ),
        Tool(
            name="get_recent_detections",
            description="Get recent person detections from face recognition",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "number",
                        "description": "Number of hours to look back (default: 24)",
                        "default": 24,
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 50)",
                        "default": 50,
                    }
                },
            },
        ),
        Tool(
            name="get_known_persons",
            description="Get list of persons with trained face recognition models",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_media_queue",
            description="Get current media playback queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status (queued, playing, played, error)",
                    }
                },
            },
        ),
        Tool(
            name="get_media_library_stats",
            description="Get statistics about the local media library",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="get_voice_command_history",
            description="Get recent voice command history",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "number",
                        "description": "Number of hours to look back (default: 24)",
                        "default": 24,
                    },
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of results (default: 20)",
                        "default": 20,
                    }
                },
            },
        ),
        Tool(
            name="search_media",
            description="Search local media library",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for filename",
                    },
                    "media_type": {
                        "type": "string",
                        "description": "Filter by type (video, audio, photo)",
                    }
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls from AI."""
    logger.info(f"MCP tool called: {name} with arguments: {arguments}")

    db = get_db()

    try:
        if name == "get_application_status":
            return await get_application_status(db)

        elif name == "get_settings":
            return await get_settings(db, arguments.get("key"))

        elif name == "get_api_integrations":
            return await get_api_integrations(db, arguments.get("enabled_only", False))

        elif name == "get_response_rules":
            return await get_response_rules(db, arguments.get("enabled_only", False))

        elif name == "get_recent_detections":
            return await get_recent_detections(
                db,
                hours=arguments.get("hours", 24),
                limit=arguments.get("limit", 50)
            )

        elif name == "get_known_persons":
            return await get_known_persons(db)

        elif name == "get_media_queue":
            return await get_media_queue(db, arguments.get("status"))

        elif name == "get_media_library_stats":
            return await get_media_library_stats(db)

        elif name == "get_voice_command_history":
            return await get_voice_command_history(
                db,
                hours=arguments.get("hours", 24),
                limit=arguments.get("limit", 20)
            )

        elif name == "search_media":
            return await search_media(
                db,
                query=arguments.get("query", ""),
                media_type=arguments.get("media_type")
            )

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# Tool implementations

async def get_application_status(db) -> List[TextContent]:
    """Get overall application status."""
    status = {
        "service": "Google Clock 2.0",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "backend": "running",
            "database": "connected",
        },
        "statistics": {
            "total_settings": db.query(SettingsModel).count(),
            "total_api_integrations": db.query(APIIntegration).count(),
            "total_rules": db.query(ResponseRule).count(),
            "total_persons": db.query(Person).count(),
            "total_detections": db.query(Detection).count(),
            "media_queue_size": db.query(MediaQueue).filter(
                MediaQueue.status.in_(["queued", "playing"])
            ).count(),
        }
    }

    return [TextContent(
        type="text",
        text=json.dumps(status, indent=2)
    )]


async def get_settings(db, key: str = None) -> List[TextContent]:
    """Get application settings."""
    if key:
        setting = db.query(SettingsModel).filter(SettingsModel.key == key).first()
        if setting:
            result = {key: setting.value}
        else:
            result = {"error": f"Setting '{key}' not found"}
    else:
        settings = db.query(SettingsModel).all()
        result = {s.key: s.value for s in settings}

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def get_api_integrations(db, enabled_only: bool = False) -> List[TextContent]:
    """Get all API integrations."""
    query = db.query(APIIntegration)

    if enabled_only:
        query = query.filter(APIIntegration.enabled == True)

    integrations = query.all()

    result = [
        {
            "id": api.id,
            "name": api.name,
            "url": api.url,
            "method": api.method,
            "enabled": api.enabled,
            "last_run": api.last_run.isoformat() if api.last_run else None,
            "next_run": api.next_run.isoformat() if api.next_run else None,
            "error_count": api.error_count,
            "schedule_interval": api.schedule_interval,
        }
        for api in integrations
    ]

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def get_response_rules(db, enabled_only: bool = False) -> List[TextContent]:
    """Get automation rules."""
    query = db.query(ResponseRule)

    if enabled_only:
        query = query.filter(ResponseRule.enabled == True)

    rules = query.all()

    result = [
        {
            "id": rule.id,
            "name": rule.name,
            "trigger_type": rule.trigger_type,
            "enabled": rule.enabled,
            "priority": rule.priority,
            "last_triggered": rule.last_triggered.isoformat() if rule.last_triggered else None,
            "trigger_count": rule.trigger_count,
            "actions": rule.actions,
        }
        for rule in rules
    ]

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def get_recent_detections(db, hours: int = 24, limit: int = 50) -> List[TextContent]:
    """Get recent person detections."""
    since = datetime.now() - timedelta(hours=hours)

    detections = db.query(Detection).filter(
        Detection.detected_at >= since
    ).order_by(
        Detection.detected_at.desc()
    ).limit(limit).all()

    result = [
        {
            "id": d.id,
            "person_id": d.person_id,
            "person_name": d.person.name if d.person else "Unknown",
            "detected_at": d.detected_at.isoformat(),
            "confidence": d.confidence,
            "first_of_day": d.first_of_day,
            "greeted": d.greeted,
        }
        for d in detections
    ]

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def get_known_persons(db) -> List[TextContent]:
    """Get list of known persons."""
    persons = db.query(Person).all()

    result = [
        {
            "id": p.id,
            "name": p.name,
            "has_face_encoding": p.face_encoding is not None,
            "photo_samples": len(p.photo_samples) if p.photo_samples else 0,
            "greetings": {
                "morning": p.greeting_morning,
                "afternoon": p.greeting_afternoon,
                "evening": p.greeting_evening,
            },
        }
        for p in persons
    ]

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def get_media_queue(db, status: str = None) -> List[TextContent]:
    """Get media playback queue."""
    query = db.query(MediaQueue)

    if status:
        query = query.filter(MediaQueue.status == status)

    items = query.order_by(MediaQueue.queued_at).all()

    result = [
        {
            "id": item.id,
            "title": item.title,
            "type": item.media_type,
            "status": item.status,
            "source": item.source,
            "duration": item.duration,
            "queued_at": item.queued_at.isoformat(),
        }
        for item in items
    ]

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def get_media_library_stats(db) -> List[TextContent]:
    """Get media library statistics."""
    stats = {
        "total_files": db.query(MediaLibrary).count(),
        "by_type": {
            "video": db.query(MediaLibrary).filter(MediaLibrary.media_type == "video").count(),
            "audio": db.query(MediaLibrary).filter(MediaLibrary.media_type == "audio").count(),
            "photo": db.query(MediaLibrary).filter(MediaLibrary.media_type == "photo").count(),
        },
        "total_size_bytes": db.query(func.sum(MediaLibrary.file_size)).scalar() or 0,
        "most_played": [
            {
                "filename": m.filename,
                "play_count": m.play_count,
                "type": m.media_type,
            }
            for m in db.query(MediaLibrary).order_by(
                MediaLibrary.play_count.desc()
            ).limit(10).all()
        ]
    }

    return [TextContent(
        type="text",
        text=json.dumps(stats, indent=2)
    )]


async def get_voice_command_history(db, hours: int = 24, limit: int = 20) -> List[TextContent]:
    """Get recent voice command history."""
    since = datetime.now() - timedelta(hours=hours)

    commands = db.query(VoiceCommand).filter(
        VoiceCommand.processed_at >= since
    ).order_by(
        VoiceCommand.processed_at.desc()
    ).limit(limit).all()

    result = [
        {
            "id": cmd.id,
            "transcript": cmd.transcript,
            "intent": cmd.intent,
            "response": cmd.response,
            "confidence": cmd.confidence,
            "processed_at": cmd.processed_at.isoformat(),
            "duration_ms": cmd.duration_ms,
        }
        for cmd in commands
    ]

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def search_media(db, query: str, media_type: str = None) -> List[TextContent]:
    """Search media library."""
    q = db.query(MediaLibrary).filter(
        MediaLibrary.filename.ilike(f"%{query}%")
    )

    if media_type:
        q = q.filter(MediaLibrary.media_type == media_type)

    results = q.limit(50).all()

    result = [
        {
            "id": m.id,
            "filename": m.filename,
            "type": m.media_type,
            "size": m.file_size,
            "duration": m.duration,
            "play_count": m.play_count,
        }
        for m in results
    ]

    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


# Run the MCP server
if __name__ == "__main__":
    import mcp.server.stdio

    async def main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    asyncio.run(main())
