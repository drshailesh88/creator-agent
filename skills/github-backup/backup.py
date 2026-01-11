#!/usr/bin/env python3
"""
GitHub Backup for Notion Pensieve

Exports Notion Pensieve database entries to Markdown files and commits
them to a private GitHub repository. Supports incremental backups.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

from notion_client import Client as NotionClient
from github import Github, GithubException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PensieveBackup:
    """Handles backup of Notion Pensieve to GitHub."""

    def __init__(
        self,
        notion_token: Optional[str] = None,
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        pensieve_database_id: Optional[str] = None,
    ):
        """
        Initialize the backup handler.

        Args:
            notion_token: Notion integration token
            github_token: GitHub personal access token
            github_repo: GitHub repository in format 'owner/repo'
            pensieve_database_id: Notion database ID for Pensieve
        """
        self.notion_token = notion_token or os.environ.get("NOTION_TOKEN")
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.github_repo = github_repo or os.environ.get("GITHUB_BACKUP_REPO")
        self.pensieve_database_id = pensieve_database_id or os.environ.get(
            "PENSIEVE_DATABASE_ID"
        )

        if not all(
            [
                self.notion_token,
                self.github_token,
                self.github_repo,
                self.pensieve_database_id,
            ]
        ):
            raise ValueError(
                "Missing required configuration. Ensure NOTION_TOKEN, GITHUB_TOKEN, "
                "GITHUB_BACKUP_REPO, and PENSIEVE_DATABASE_ID are set."
            )

        self.notion = NotionClient(auth=self.notion_token)
        self.github = Github(self.github_token)
        self.repo = self.github.get_repo(self.github_repo)

        # Local cache for tracking what's been backed up
        self.cache_file = Path.home() / ".pensieve_backup_cache.json"
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load the backup cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Cache file corrupted, starting fresh")
        return {"entries": {}, "last_backup": None}

    def _save_cache(self):
        """Save the backup cache to disk."""
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2, default=str)

    def _get_entry_hash(self, entry: dict) -> str:
        """Generate a hash for an entry to detect changes."""
        content = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _extract_title(self, page: dict) -> str:
        """Extract the title from a Notion page."""
        properties = page.get("properties", {})

        # Try common title property names
        for prop_name in ["Name", "Title", "name", "title"]:
            if prop_name in properties:
                prop = properties[prop_name]
                if prop.get("type") == "title":
                    title_content = prop.get("title", [])
                    if title_content:
                        return title_content[0].get("plain_text", "Untitled")

        return "Untitled"

    def _extract_date(self, page: dict) -> datetime:
        """Extract the date from a Notion page."""
        properties = page.get("properties", {})

        # Try common date property names
        for prop_name in ["Date", "Created", "date", "created"]:
            if prop_name in properties:
                prop = properties[prop_name]
                if prop.get("type") == "date" and prop.get("date"):
                    date_str = prop["date"].get("start")
                    if date_str:
                        # Parse ISO format date
                        if "T" in date_str:
                            return datetime.fromisoformat(
                                date_str.replace("Z", "+00:00")
                            )
                        return datetime.strptime(date_str, "%Y-%m-%d")

        # Fall back to created_time
        created_time = page.get("created_time")
        if created_time:
            return datetime.fromisoformat(created_time.replace("Z", "+00:00"))

        return datetime.now(timezone.utc)

    def _extract_properties(self, page: dict) -> dict:
        """Extract all properties as metadata."""
        metadata = {
            "id": page.get("id"),
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
            "url": page.get("url"),
        }

        properties = page.get("properties", {})
        for prop_name, prop_value in properties.items():
            prop_type = prop_value.get("type")

            if prop_type == "title":
                continue  # Already handled
            elif prop_type == "rich_text":
                texts = prop_value.get("rich_text", [])
                metadata[prop_name] = " ".join(t.get("plain_text", "") for t in texts)
            elif prop_type == "select":
                select = prop_value.get("select")
                metadata[prop_name] = select.get("name") if select else None
            elif prop_type == "multi_select":
                options = prop_value.get("multi_select", [])
                metadata[prop_name] = [opt.get("name") for opt in options]
            elif prop_type == "date":
                date = prop_value.get("date")
                metadata[prop_name] = date.get("start") if date else None
            elif prop_type == "checkbox":
                metadata[prop_name] = prop_value.get("checkbox", False)
            elif prop_type == "number":
                metadata[prop_name] = prop_value.get("number")
            elif prop_type == "url":
                metadata[prop_name] = prop_value.get("url")

        return metadata

    def _get_page_content(self, page_id: str) -> str:
        """Retrieve the content blocks of a Notion page."""
        blocks = []
        cursor = None

        while True:
            response = self.notion.blocks.children.list(
                block_id=page_id, start_cursor=cursor
            )

            for block in response.get("results", []):
                block_text = self._block_to_markdown(block)
                if block_text:
                    blocks.append(block_text)

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return "\n\n".join(blocks)

    def _block_to_markdown(self, block: dict) -> str:
        """Convert a Notion block to Markdown."""
        block_type = block.get("type")

        if block_type == "paragraph":
            return self._rich_text_to_markdown(
                block.get("paragraph", {}).get("rich_text", [])
            )

        elif block_type == "heading_1":
            text = self._rich_text_to_markdown(
                block.get("heading_1", {}).get("rich_text", [])
            )
            return f"# {text}"

        elif block_type == "heading_2":
            text = self._rich_text_to_markdown(
                block.get("heading_2", {}).get("rich_text", [])
            )
            return f"## {text}"

        elif block_type == "heading_3":
            text = self._rich_text_to_markdown(
                block.get("heading_3", {}).get("rich_text", [])
            )
            return f"### {text}"

        elif block_type == "bulleted_list_item":
            text = self._rich_text_to_markdown(
                block.get("bulleted_list_item", {}).get("rich_text", [])
            )
            return f"- {text}"

        elif block_type == "numbered_list_item":
            text = self._rich_text_to_markdown(
                block.get("numbered_list_item", {}).get("rich_text", [])
            )
            return f"1. {text}"

        elif block_type == "to_do":
            todo = block.get("to_do", {})
            text = self._rich_text_to_markdown(todo.get("rich_text", []))
            checked = "x" if todo.get("checked") else " "
            return f"- [{checked}] {text}"

        elif block_type == "toggle":
            text = self._rich_text_to_markdown(
                block.get("toggle", {}).get("rich_text", [])
            )
            return f"<details><summary>{text}</summary></details>"

        elif block_type == "code":
            code_block = block.get("code", {})
            text = self._rich_text_to_markdown(code_block.get("rich_text", []))
            language = code_block.get("language", "")
            return f"```{language}\n{text}\n```"

        elif block_type == "quote":
            text = self._rich_text_to_markdown(
                block.get("quote", {}).get("rich_text", [])
            )
            return f"> {text}"

        elif block_type == "divider":
            return "---"

        elif block_type == "callout":
            callout = block.get("callout", {})
            text = self._rich_text_to_markdown(callout.get("rich_text", []))
            icon = callout.get("icon", {}).get("emoji", "")
            return f"> {icon} {text}"

        elif block_type == "image":
            image = block.get("image", {})
            url = image.get("file", {}).get("url") or image.get("external", {}).get(
                "url"
            )
            caption = self._rich_text_to_markdown(image.get("caption", []))
            return f"![{caption}]({url})"

        return ""

    def _rich_text_to_markdown(self, rich_text: list) -> str:
        """Convert Notion rich text to Markdown."""
        result = []

        for text in rich_text:
            content = text.get("plain_text", "")
            annotations = text.get("annotations", {})

            if annotations.get("bold"):
                content = f"**{content}**"
            if annotations.get("italic"):
                content = f"*{content}*"
            if annotations.get("strikethrough"):
                content = f"~~{content}~~"
            if annotations.get("code"):
                content = f"`{content}`"

            href = text.get("href")
            if href:
                content = f"[{content}]({href})"

            result.append(content)

        return "".join(result)

    def _page_to_markdown(self, page: dict) -> str:
        """Convert a complete Notion page to Markdown with YAML frontmatter."""
        title = self._extract_title(page)
        metadata = self._extract_properties(page)
        content = self._get_page_content(page["id"])

        # Build YAML frontmatter
        frontmatter_lines = ["---"]
        frontmatter_lines.append(f"title: \"{title}\"")

        for key, value in metadata.items():
            if value is not None:
                if isinstance(value, list):
                    frontmatter_lines.append(f"{key}:")
                    for item in value:
                        frontmatter_lines.append(f"  - \"{item}\"")
                elif isinstance(value, bool):
                    frontmatter_lines.append(f"{key}: {str(value).lower()}")
                elif isinstance(value, str) and "\n" not in value:
                    frontmatter_lines.append(f"{key}: \"{value}\"")
                else:
                    frontmatter_lines.append(f"{key}: {value}")

        frontmatter_lines.append("---")

        frontmatter = "\n".join(frontmatter_lines)
        return f"{frontmatter}\n\n# {title}\n\n{content}"

    def _get_github_file_path(self, entry_date: datetime) -> str:
        """Generate the GitHub file path for a backup entry."""
        return f"pensieve/{entry_date.year}/{entry_date.month:02d}/{entry_date.strftime('%Y-%m-%d')}.md"

    def fetch_pensieve_entries(self, since: Optional[datetime] = None) -> list:
        """
        Fetch entries from Pensieve database.

        Args:
            since: Only fetch entries modified after this time

        Returns:
            List of Notion page objects
        """
        entries = []
        cursor = None

        filter_params = {}
        if since:
            filter_params["filter"] = {
                "timestamp": "last_edited_time",
                "last_edited_time": {"after": since.isoformat()},
            }

        while True:
            response = self.notion.databases.query(
                database_id=self.pensieve_database_id,
                start_cursor=cursor,
                **filter_params,
            )

            entries.extend(response.get("results", []))

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return entries

    def backup_entry(self, page: dict) -> bool:
        """
        Backup a single Pensieve entry to GitHub.

        Args:
            page: Notion page object

        Returns:
            True if the entry was backed up, False if unchanged
        """
        page_id = page["id"]
        entry_hash = self._get_entry_hash(page)

        # Check if entry has changed
        if self.cache["entries"].get(page_id) == entry_hash:
            logger.debug(f"Entry {page_id} unchanged, skipping")
            return False

        # Convert to Markdown
        markdown_content = self._page_to_markdown(page)
        entry_date = self._extract_date(page)
        file_path = self._get_github_file_path(entry_date)

        # Check if file exists and append or create
        try:
            existing_file = self.repo.get_contents(file_path)
            existing_content = existing_file.decoded_content.decode("utf-8")

            # Append new entry with separator
            new_content = f"{existing_content}\n\n---\n\n{markdown_content}"

            self.repo.update_file(
                path=file_path,
                message=f"Update Pensieve backup: {entry_date.strftime('%Y-%m-%d')}",
                content=new_content,
                sha=existing_file.sha,
            )
            logger.info(f"Updated {file_path}")

        except GithubException as e:
            if e.status == 404:
                # File doesn't exist, create it
                self.repo.create_file(
                    path=file_path,
                    message=f"Add Pensieve backup: {entry_date.strftime('%Y-%m-%d')}",
                    content=markdown_content,
                )
                logger.info(f"Created {file_path}")
            else:
                raise

        # Update cache
        self.cache["entries"][page_id] = entry_hash
        return True

    def run_backup(self, full: bool = False) -> dict:
        """
        Run the backup process.

        Args:
            full: If True, backup all entries. If False, only backup changed entries.

        Returns:
            Dictionary with backup statistics
        """
        logger.info("Starting Pensieve backup...")

        since = None
        if not full and self.cache.get("last_backup"):
            since = datetime.fromisoformat(self.cache["last_backup"])

        entries = self.fetch_pensieve_entries(since=since)
        logger.info(f"Found {len(entries)} entries to process")

        backed_up = 0
        skipped = 0
        errors = []

        for entry in entries:
            try:
                if self.backup_entry(entry):
                    backed_up += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Error backing up entry {entry['id']}: {e}")
                errors.append({"id": entry["id"], "error": str(e)})

        # Update last backup time
        self.cache["last_backup"] = datetime.now(timezone.utc).isoformat()
        self._save_cache()

        result = {
            "success": True,
            "backed_up": backed_up,
            "skipped": skipped,
            "errors": errors,
            "timestamp": self.cache["last_backup"],
        }

        logger.info(
            f"Backup complete: {backed_up} backed up, {skipped} skipped, {len(errors)} errors"
        )
        return result

    def get_backup_status(self) -> dict:
        """Get the current backup status."""
        return {
            "last_backup": self.cache.get("last_backup"),
            "total_entries_cached": len(self.cache.get("entries", {})),
            "repository": self.github_repo,
        }

    def list_recent_backups(self, limit: int = 10) -> list:
        """
        List recent backup commits from GitHub.

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of backup commit information
        """
        commits = self.repo.get_commits(path="pensieve/")
        recent = []

        for i, commit in enumerate(commits):
            if i >= limit:
                break
            recent.append(
                {
                    "sha": commit.sha[:7],
                    "message": commit.commit.message,
                    "date": commit.commit.author.date.isoformat(),
                    "author": commit.commit.author.name,
                }
            )

        return recent


def main():
    """CLI entry point for manual backup."""
    import argparse

    parser = argparse.ArgumentParser(description="Backup Notion Pensieve to GitHub")
    parser.add_argument("--full", action="store_true", help="Run a full backup")
    parser.add_argument("--status", action="store_true", help="Show backup status")
    parser.add_argument("--list", action="store_true", help="List recent backups")

    args = parser.parse_args()

    backup = PensieveBackup()

    if args.status:
        status = backup.get_backup_status()
        print(json.dumps(status, indent=2))
    elif args.list:
        backups = backup.list_recent_backups()
        print(json.dumps(backups, indent=2))
    else:
        result = backup.run_backup(full=args.full)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
