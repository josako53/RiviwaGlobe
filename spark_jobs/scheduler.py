"""
APScheduler – submits batch Spark jobs on a cron schedule and manages
the lifetime of streaming jobs launched at startup.

Streaming jobs (started as subprocesses via entrypoint.sh before this
process runs) are monitored; if one dies it is restarted automatically.

Schedule
--------
  historical_analytics.py  →  every hour at :00
  staff_analytics.py        →  daily at 03:00
  ml_escalation.py          →  daily at 04:00
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger("scheduler")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SPARK_MASTER = os.getenv("SPARK_MASTER", "spark://spark_master:7077")
SPARK_PACKAGES = (
    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
    "org.postgresql:postgresql:42.6.0"
)
JOBS_DIR = Path(__file__).parent / "jobs"
STREAMING_DIR = JOBS_DIR / "streaming"
BATCH_DIR = JOBS_DIR / "batch"

STREAMING_JOBS = [
    str(STREAMING_DIR / "sla_monitor.py"),
    str(STREAMING_DIR / "hotspot_detector.py"),
    str(STREAMING_DIR / "live_dashboard.py"),
]

BATCH_JOBS = {
    "historical_analytics": str(BATCH_DIR / "historical_analytics.py"),
    "staff_analytics": str(BATCH_DIR / "staff_analytics.py"),
    "ml_escalation": str(BATCH_DIR / "ml_escalation.py"),
}

# Map of job_script_path → running subprocess
_streaming_processes: dict[str, subprocess.Popen] = {}


# ---------------------------------------------------------------------------
# spark-submit helper
# ---------------------------------------------------------------------------

def spark_submit(script_path: str, extra_args: list[str] | None = None) -> subprocess.Popen:
    """Launch spark-submit for a given script and return the Popen handle."""
    cmd = [
        "spark-submit",
        "--master", SPARK_MASTER,
        "--packages", SPARK_PACKAGES,
    ]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(script_path)

    logger.info("Launching: %s", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc


# ---------------------------------------------------------------------------
# Streaming job management
# ---------------------------------------------------------------------------

def start_streaming_job(script_path: str) -> None:
    """Start a streaming job and register it."""
    proc = spark_submit(script_path)
    _streaming_processes[script_path] = proc
    logger.info("Started streaming job PID=%d: %s", proc.pid, script_path)


def start_all_streaming_jobs() -> None:
    """Start all streaming jobs at scheduler startup."""
    for script in STREAMING_JOBS:
        if not Path(script).exists():
            logger.warning("Streaming job script not found: %s", script)
            continue
        try:
            start_streaming_job(script)
        except Exception as exc:
            logger.error("Failed to start %s: %s", script, exc)


def check_and_restart_streaming_jobs() -> None:
    """
    Watchdog: poll each registered streaming process.
    If it has exited, restart it.
    """
    for script, proc in list(_streaming_processes.items()):
        ret = proc.poll()
        if ret is not None:
            logger.warning(
                "Streaming job %s exited with code %d – restarting",
                script,
                ret,
            )
            try:
                start_streaming_job(script)
            except Exception as exc:
                logger.error("Failed to restart %s: %s", script, exc)


# ---------------------------------------------------------------------------
# Batch job runners (called by APScheduler)
# ---------------------------------------------------------------------------

def run_batch_job(name: str) -> None:
    script = BATCH_JOBS.get(name)
    if not script or not Path(script).exists():
        logger.error("Batch job script not found for '%s': %s", name, script)
        return

    logger.info("Submitting batch job '%s' at %s", name, datetime.now(timezone.utc).isoformat())
    try:
        proc = spark_submit(script)
        stdout, _ = proc.communicate(timeout=3600)  # max 1 hour
        if proc.returncode == 0:
            logger.info("Batch job '%s' completed successfully", name)
        else:
            logger.error(
                "Batch job '%s' failed with code %d.\nOutput:\n%s",
                name,
                proc.returncode,
                stdout[-4000:] if stdout else "(no output)",
            )
    except subprocess.TimeoutExpired:
        proc.kill()
        logger.error("Batch job '%s' timed out after 1 hour – killed", name)
    except Exception as exc:
        logger.error("Batch job '%s' raised exception: %s", name, exc)


def run_historical_analytics() -> None:
    run_batch_job("historical_analytics")


def run_staff_analytics() -> None:
    run_batch_job("staff_analytics")


def run_ml_escalation() -> None:
    run_batch_job("ml_escalation")


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

def _shutdown(signum, frame) -> None:
    logger.info("Received signal %d – shutting down streaming jobs", signum)
    for script, proc in _streaming_processes.items():
        if proc.poll() is None:
            logger.info("Terminating PID=%d (%s)", proc.pid, script)
            proc.terminate()
    # Give processes 10 s to clean up, then kill
    time.sleep(10)
    for script, proc in _streaming_processes.items():
        if proc.poll() is None:
            logger.warning("Killing PID=%d (%s)", proc.pid, script)
            proc.kill()
    sys.exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Spark jobs scheduler starting")

    # Start all streaming jobs
    start_all_streaming_jobs()

    scheduler = BlockingScheduler(timezone="UTC")

    # Watchdog: every 2 minutes check streaming job health
    scheduler.add_job(
        check_and_restart_streaming_jobs,
        trigger=CronTrigger(minute="*/2"),
        id="streaming_watchdog",
        name="Streaming Job Watchdog",
        max_instances=1,
        coalesce=True,
    )

    # Historical analytics: every hour at :00
    scheduler.add_job(
        run_historical_analytics,
        trigger=CronTrigger(minute=0),
        id="historical_analytics",
        name="Historical Analytics (hourly)",
        max_instances=1,
        coalesce=True,
    )

    # Staff analytics: daily at 03:00 UTC
    scheduler.add_job(
        run_staff_analytics,
        trigger=CronTrigger(hour=3, minute=0),
        id="staff_analytics",
        name="Staff Analytics (nightly 03:00)",
        max_instances=1,
        coalesce=True,
    )

    # ML escalation scoring: daily at 04:00 UTC
    scheduler.add_job(
        run_ml_escalation,
        trigger=CronTrigger(hour=4, minute=0),
        id="ml_escalation",
        name="ML Escalation Scoring (nightly 04:00)",
        max_instances=1,
        coalesce=True,
    )

    logger.info("Scheduler configured. Jobs registered: %s", [j.id for j in scheduler.get_jobs()])
    logger.info("Entering blocking scheduler loop …")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
        _shutdown(0, None)


if __name__ == "__main__":
    main()
