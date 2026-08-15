"""
Unit test — scheduler configuration regression.

Verifies that the APScheduler daily_snapshot job is registered with a CronTrigger
configured for 00:00 Asia/Kolkata.

This catches a regression where someone removes the CronTrigger or changes the
schedule inadvertently.
"""

from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger

from app.jobs.scheduler import _run_daily_snapshot, start_scheduler


class TestSchedulerConfiguration:
    def test_daily_snapshot_job_has_cron_trigger_at_midnight_ist(self):
        """
        The 'daily_snapshot' job must be registered with a CronTrigger
        configured for hour=0, minute=0, timezone=Asia/Kolkata.
        """
        from unittest.mock import MagicMock

        from apscheduler.schedulers.background import BackgroundScheduler

        # Create a real scheduler but don't start it — inspect its config
        fake_app = MagicMock()

        # start_scheduler uses the module-level _scheduler global,
        # so we call it and then inspect the registered job.
        start_scheduler(fake_app)

        # Import the module-level scheduler instance
        from app.jobs import scheduler as sched_module

        scheduler_instance: BackgroundScheduler = sched_module._scheduler
        assert scheduler_instance is not None

        job = scheduler_instance.get_job("daily_snapshot")
        assert job is not None, "daily_snapshot job not registered"

        trigger = job.trigger
        assert isinstance(trigger, CronTrigger), (
            f"Expected CronTrigger, got {type(trigger).__name__}"
        )

        # Verify the cron fields
        # CronTrigger stores fields as CronExpression objects; access .expressions
        hour_field = trigger.fields[trigger.FIELD_NAMES.index("hour")]
        minute_field = trigger.fields[trigger.FIELD_NAMES.index("minute")]

        assert str(hour_field) == "0", f"Expected hour=0, got {hour_field}"
        assert str(minute_field) == "0", f"Expected minute=0, got {minute_field}"

        # Verify timezone
        assert trigger.timezone == ZoneInfo("Asia/Kolkata"), (
            f"Expected Asia/Kolkata, got {trigger.timezone}"
        )

        # Verify the job func is the correct function
        assert job.func == _run_daily_snapshot

        # Clean up — shut down the scheduler
        if scheduler_instance.running:
            scheduler_instance.shutdown(wait=False)
