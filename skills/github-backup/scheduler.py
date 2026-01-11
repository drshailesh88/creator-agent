#!/usr/bin/env python3
"""
Scheduler for Pensieve GitHub Backups

Provides configurable scheduling for automatic backups using APScheduler.
Supports weekly, daily, and custom schedules.
"""

import os
import json
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from backup import PensieveBackup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class BackupScheduler:
    """Manages scheduled backups of Pensieve to GitHub."""

    CONFIG_FILE = Path.home() / ".pensieve_backup_schedule.json"
    JOB_ID = "pensieve_backup"

    # Preset schedules
    SCHEDULES = {
        "weekly": {"day_of_week": "sun", "hour": 3, "minute": 0},
        "daily": {"hour": 3, "minute": 0},
        "twice_daily": {"hour": "3,15", "minute": 0},
        "hourly": {"minute": 0},
    }

    def __init__(self, on_backup_complete: Optional[Callable] = None):
        """
        Initialize the backup scheduler.

        Args:
            on_backup_complete: Optional callback function called after each backup
        """
        self.on_backup_complete = on_backup_complete
        self.config = self._load_config()

        # Configure APScheduler
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(1)}
        job_defaults = {"coalesce": True, "max_instances": 1}

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )

        self._backup_instance = None

    def _load_config(self) -> dict:
        """Load scheduler configuration from disk."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                logger.warning("Config file corrupted, using defaults")

        return {
            "schedule_type": "weekly",
            "custom_cron": None,
            "enabled": True,
            "notify_on_complete": True,
            "notify_on_error": True,
        }

    def _save_config(self):
        """Save scheduler configuration to disk."""
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def _get_backup_instance(self) -> PensieveBackup:
        """Get or create the backup instance."""
        if self._backup_instance is None:
            self._backup_instance = PensieveBackup()
        return self._backup_instance

    def _run_backup_job(self):
        """Execute the backup job."""
        logger.info("Starting scheduled backup...")

        try:
            backup = self._get_backup_instance()
            result = backup.run_backup(full=False)

            logger.info(
                f"Scheduled backup complete: {result['backed_up']} entries backed up"
            )

            if self.on_backup_complete:
                self.on_backup_complete(result)

            # Log to history
            self._log_backup_result(result)

            return result

        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if self.on_backup_complete:
                self.on_backup_complete(error_result)

            self._log_backup_result(error_result)
            raise

    def _log_backup_result(self, result: dict):
        """Log backup result to history file."""
        history_file = Path.home() / ".pensieve_backup_history.json"

        history = []
        if history_file.exists():
            try:
                with open(history_file, "r") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        # Keep last 100 entries
        history.append(result)
        history = history[-100:]

        with open(history_file, "w") as f:
            json.dump(history, f, indent=2)

    def set_schedule(
        self,
        schedule_type: str = "weekly",
        custom_cron: Optional[str] = None,
    ) -> dict:
        """
        Set the backup schedule.

        Args:
            schedule_type: One of 'weekly', 'daily', 'twice_daily', 'hourly', 'custom'
            custom_cron: Cron expression for custom schedule (required if type is 'custom')

        Returns:
            Dictionary with schedule details
        """
        if schedule_type == "custom":
            if not custom_cron:
                raise ValueError("custom_cron is required for custom schedule type")
            trigger = CronTrigger.from_crontab(custom_cron)
            self.config["custom_cron"] = custom_cron
        elif schedule_type in self.SCHEDULES:
            trigger = CronTrigger(**self.SCHEDULES[schedule_type])
            self.config["custom_cron"] = None
        else:
            raise ValueError(
                f"Invalid schedule_type: {schedule_type}. "
                f"Must be one of: {', '.join(self.SCHEDULES.keys())}, custom"
            )

        self.config["schedule_type"] = schedule_type
        self._save_config()

        # Update the job if scheduler is running
        if self.scheduler.running:
            self.scheduler.remove_job(self.JOB_ID, jobstore="default")
            self.scheduler.add_job(
                self._run_backup_job,
                trigger=trigger,
                id=self.JOB_ID,
                name="Pensieve Backup",
                replace_existing=True,
            )

        logger.info(f"Backup schedule set to: {schedule_type}")

        return {
            "schedule_type": schedule_type,
            "custom_cron": custom_cron,
            "next_run": self._get_next_run_time(),
        }

    def _get_next_run_time(self) -> Optional[str]:
        """Get the next scheduled run time."""
        job = self.scheduler.get_job(self.JOB_ID)
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return None

    def start(self):
        """Start the scheduler."""
        if not self.config.get("enabled", True):
            logger.info("Scheduler is disabled, not starting")
            return

        # Set up the trigger based on config
        schedule_type = self.config.get("schedule_type", "weekly")

        if schedule_type == "custom" and self.config.get("custom_cron"):
            trigger = CronTrigger.from_crontab(self.config["custom_cron"])
        elif schedule_type in self.SCHEDULES:
            trigger = CronTrigger(**self.SCHEDULES[schedule_type])
        else:
            trigger = CronTrigger(**self.SCHEDULES["weekly"])

        self.scheduler.add_job(
            self._run_backup_job,
            trigger=trigger,
            id=self.JOB_ID,
            name="Pensieve Backup",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info(f"Scheduler started with {schedule_type} schedule")
        logger.info(f"Next backup: {self._get_next_run_time()}")

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def pause(self):
        """Pause scheduled backups."""
        self.scheduler.pause_job(self.JOB_ID)
        self.config["enabled"] = False
        self._save_config()
        logger.info("Scheduled backups paused")

    def resume(self):
        """Resume scheduled backups."""
        self.scheduler.resume_job(self.JOB_ID)
        self.config["enabled"] = True
        self._save_config()
        logger.info("Scheduled backups resumed")

    def trigger_now(self) -> dict:
        """Trigger an immediate backup."""
        logger.info("Manual backup triggered")
        return self._run_backup_job()

    def get_status(self) -> dict:
        """Get scheduler status."""
        job = self.scheduler.get_job(self.JOB_ID)

        return {
            "running": self.scheduler.running,
            "enabled": self.config.get("enabled", True),
            "schedule_type": self.config.get("schedule_type", "weekly"),
            "custom_cron": self.config.get("custom_cron"),
            "next_run": self._get_next_run_time(),
            "job_exists": job is not None,
        }

    def get_history(self, limit: int = 10) -> list:
        """
        Get backup history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of backup results
        """
        history_file = Path.home() / ".pensieve_backup_history.json"

        if not history_file.exists():
            return []

        try:
            with open(history_file, "r") as f:
                history = json.load(f)
            return history[-limit:][::-1]  # Most recent first
        except (json.JSONDecodeError, IOError):
            return []


def run_daemon():
    """Run the scheduler as a daemon process."""
    scheduler = BackupScheduler()

    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    scheduler.start()

    # Keep the main thread alive
    try:
        while True:
            signal.pause()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()


def main():
    """CLI entry point for scheduler management."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage Pensieve backup scheduler")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Start command
    subparsers.add_parser("start", help="Start the scheduler daemon")

    # Status command
    subparsers.add_parser("status", help="Show scheduler status")

    # History command
    history_parser = subparsers.add_parser("history", help="Show backup history")
    history_parser.add_argument(
        "--limit", type=int, default=10, help="Number of entries to show"
    )

    # Set schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Set backup schedule")
    schedule_parser.add_argument(
        "type",
        choices=["weekly", "daily", "twice_daily", "hourly", "custom"],
        help="Schedule type",
    )
    schedule_parser.add_argument("--cron", help="Cron expression for custom schedule")

    # Trigger command
    subparsers.add_parser("trigger", help="Trigger immediate backup")

    args = parser.parse_args()

    if args.command == "start":
        run_daemon()

    else:
        scheduler = BackupScheduler()

        if args.command == "status":
            status = scheduler.get_status()
            print(json.dumps(status, indent=2))

        elif args.command == "history":
            history = scheduler.get_history(limit=args.limit)
            print(json.dumps(history, indent=2))

        elif args.command == "schedule":
            result = scheduler.set_schedule(
                schedule_type=args.type,
                custom_cron=args.cron if args.type == "custom" else None,
            )
            print(json.dumps(result, indent=2))

        elif args.command == "trigger":
            result = scheduler.trigger_now()
            print(json.dumps(result, indent=2))

        else:
            parser.print_help()


if __name__ == "__main__":
    main()
