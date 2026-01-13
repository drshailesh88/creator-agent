"""Notion database schemas for the scratchpad system.

Defines the property schemas for Sessions, Documents, and Notes databases
that store scratchpad data in Notion.
"""

from typing import Any, Dict, List, TypedDict


class PropertySchema(TypedDict, total=False):
    """Schema definition for a Notion database property."""
    type: str
    options: List[str]


# Sessions database schema
SESSIONS_SCHEMA: Dict[str, PropertySchema] = {
    "Session ID": {"type": "title"},
    "Task": {"type": "rich_text"},
    "Status": {
        "type": "select",
        "options": ["active", "paused", "complete"]
    },
    "Documents": {"type": "relation"},  # Links to Documents DB
    "Notes": {"type": "relation"},  # Links to Notes DB
    "Context Refreshes": {"type": "number"},
    "Created": {"type": "created_time"},
    "Updated": {"type": "last_edited_time"}
}

# Documents database schema
DOCUMENTS_SCHEMA: Dict[str, PropertySchema] = {
    "Document ID": {"type": "title"},
    "Session": {"type": "relation"},
    "Path": {"type": "rich_text"},
    "Title": {"type": "rich_text"},
    "Total Pages": {"type": "number"},
    "Processed Pages": {"type": "number"},
    "Status": {
        "type": "select",
        "options": ["pending", "in_progress", "complete"]
    },
    "Position": {"type": "rich_text"}
}

# Notes database schema
NOTES_SCHEMA: Dict[str, PropertySchema] = {
    "Note ID": {"type": "title"},
    "Session": {"type": "relation"},
    "Document": {"type": "relation"},
    "Content": {"type": "rich_text"},
    "Citations": {"type": "multi_select"},
    "Created": {"type": "created_time"}
}


def build_sessions_properties(
    documents_db_id: str,
    notes_db_id: str
) -> Dict[str, Any]:
    """
    Build the complete Notion properties object for creating a Sessions database.

    Args:
        documents_db_id: The Notion database ID for the Documents database
        notes_db_id: The Notion database ID for the Notes database

    Returns:
        Dict containing the full property definitions for Notion API
    """
    return {
        "Session ID": {"title": {}},
        "Task": {"rich_text": {}},
        "Status": {
            "select": {
                "options": [
                    {"name": "active", "color": "green"},
                    {"name": "paused", "color": "yellow"},
                    {"name": "complete", "color": "blue"}
                ]
            }
        },
        "Documents": {
            "relation": {
                "database_id": documents_db_id,
                "type": "dual_property",
                "dual_property": {}
            }
        },
        "Notes": {
            "relation": {
                "database_id": notes_db_id,
                "type": "dual_property",
                "dual_property": {}
            }
        },
        "Context Refreshes": {"number": {"format": "number"}},
    }


def build_documents_properties(sessions_db_id: str) -> Dict[str, Any]:
    """
    Build the complete Notion properties object for creating a Documents database.

    Args:
        sessions_db_id: The Notion database ID for the Sessions database

    Returns:
        Dict containing the full property definitions for Notion API
    """
    return {
        "Document ID": {"title": {}},
        "Session": {
            "relation": {
                "database_id": sessions_db_id,
                "type": "dual_property",
                "dual_property": {}
            }
        },
        "Path": {"rich_text": {}},
        "Title": {"rich_text": {}},
        "Total Pages": {"number": {"format": "number"}},
        "Processed Pages": {"number": {"format": "number"}},
        "Status": {
            "select": {
                "options": [
                    {"name": "pending", "color": "gray"},
                    {"name": "in_progress", "color": "yellow"},
                    {"name": "complete", "color": "green"}
                ]
            }
        },
        "Position": {"rich_text": {}},
    }


def build_notes_properties(
    sessions_db_id: str,
    documents_db_id: str
) -> Dict[str, Any]:
    """
    Build the complete Notion properties object for creating a Notes database.

    Args:
        sessions_db_id: The Notion database ID for the Sessions database
        documents_db_id: The Notion database ID for the Documents database

    Returns:
        Dict containing the full property definitions for Notion API
    """
    return {
        "Note ID": {"title": {}},
        "Session": {
            "relation": {
                "database_id": sessions_db_id,
                "type": "dual_property",
                "dual_property": {}
            }
        },
        "Document": {
            "relation": {
                "database_id": documents_db_id,
                "type": "dual_property",
                "dual_property": {}
            }
        },
        "Content": {"rich_text": {}},
        "Citations": {"multi_select": {"options": []}},
    }


# Property name mappings for converting between model fields and Notion properties
SESSION_FIELD_MAP = {
    "session_id": "Session ID",
    "task": "Task",
    "status": "Status",
    "documents": "Documents",
    "notes": "Notes",
    "context_refreshes": "Context Refreshes",
    "created_at": "Created",
    "updated_at": "Updated"
}

DOCUMENT_FIELD_MAP = {
    "document_id": "Document ID",
    "session_id": "Session",
    "path": "Path",
    "title": "Title",
    "total_pages": "Total Pages",
    "processed_pages": "Processed Pages",
    "status": "Status",
    "position": "Position"
}

NOTE_FIELD_MAP = {
    "note_id": "Note ID",
    "session_id": "Session",
    "document_id": "Document",
    "content": "Content",
    "citations": "Citations",
    "created_at": "Created"
}


# Reverse mappings for reading from Notion
SESSION_PROPERTY_MAP = {v: k for k, v in SESSION_FIELD_MAP.items()}
DOCUMENT_PROPERTY_MAP = {v: k for k, v in DOCUMENT_FIELD_MAP.items()}
NOTE_PROPERTY_MAP = {v: k for k, v in NOTE_FIELD_MAP.items()}


def extract_rich_text(prop: Dict[str, Any]) -> str:
    """Extract plain text from a Notion rich_text property."""
    if not prop or not prop.get("rich_text"):
        return ""
    return "".join(rt.get("plain_text", "") for rt in prop["rich_text"])


def extract_title(prop: Dict[str, Any]) -> str:
    """Extract plain text from a Notion title property."""
    if not prop or not prop.get("title"):
        return ""
    return "".join(t.get("plain_text", "") for t in prop["title"])


def extract_select(prop: Dict[str, Any]) -> str:
    """Extract the selected value from a Notion select property."""
    if not prop or not prop.get("select"):
        return ""
    return prop["select"].get("name", "")


def extract_multi_select(prop: Dict[str, Any]) -> List[str]:
    """Extract all selected values from a Notion multi_select property."""
    if not prop or not prop.get("multi_select"):
        return []
    return [item.get("name", "") for item in prop["multi_select"]]


def extract_number(prop: Dict[str, Any]) -> int:
    """Extract the number from a Notion number property."""
    if not prop:
        return 0
    return prop.get("number") or 0


def extract_relation(prop: Dict[str, Any]) -> List[str]:
    """Extract page IDs from a Notion relation property."""
    if not prop or not prop.get("relation"):
        return []
    return [rel.get("id", "") for rel in prop["relation"]]


def extract_created_time(prop: Dict[str, Any]) -> str:
    """Extract the timestamp from a Notion created_time property."""
    if not prop:
        return ""
    return prop.get("created_time", "")


def extract_last_edited_time(prop: Dict[str, Any]) -> str:
    """Extract the timestamp from a Notion last_edited_time property."""
    if not prop:
        return ""
    return prop.get("last_edited_time", "")


def build_rich_text(text: str) -> Dict[str, Any]:
    """Build a Notion rich_text property value."""
    return {
        "rich_text": [
            {
                "type": "text",
                "text": {"content": text[:2000]}  # Notion limit per block
            }
        ]
    }


def build_title(text: str) -> Dict[str, Any]:
    """Build a Notion title property value."""
    return {
        "title": [
            {
                "type": "text",
                "text": {"content": text[:2000]}
            }
        ]
    }


def build_select(value: str) -> Dict[str, Any]:
    """Build a Notion select property value."""
    return {"select": {"name": value}}


def build_multi_select(values: List[str]) -> Dict[str, Any]:
    """Build a Notion multi_select property value."""
    return {"multi_select": [{"name": v} for v in values]}


def build_number(value: int) -> Dict[str, Any]:
    """Build a Notion number property value."""
    return {"number": value}


def build_relation(page_ids: List[str]) -> Dict[str, Any]:
    """Build a Notion relation property value."""
    return {"relation": [{"id": pid} for pid in page_ids]}
