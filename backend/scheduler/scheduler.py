import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_due_analyses() -> None:
    from backend.db.client import get_db
    from backend.db.analyses import create_analysis
    from backend.agent.supplier_agent import run_supplier_agent

    db = get_db()
    res = db.table("suppliers_view").select("id,name,last_analyzed,user_id").execute()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=settings.scheduler_interval_days)).isoformat()

    due = [s for s in res.data if s["last_analyzed"] is None or s["last_analyzed"] < cutoff]

    if not due:
        logger.info("Scheduler: no suppliers due for analysis")
        return

    logger.info(f"Scheduler: {len(due)} suppliers due for re-analysis")
    for supplier in due:
        try:
            analysis = create_analysis(supplier["id"], supplier["user_id"], "scheduler")
            run_supplier_agent(supplier["id"], supplier["user_id"], "scheduler", analysis)
            logger.info(f"Scheduler: done — {supplier['name']}")
        except Exception as e:
            logger.error(f"Scheduler: error on {supplier['name']}: {e}")


def start_scheduler() -> None:
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=false)")
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_due_analyses,
        trigger=IntervalTrigger(hours=settings.scheduler_check_hours),
        id="check_due_analyses",
        name="Re-analyze suppliers past interval",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        f"Scheduler started — checks every {settings.scheduler_check_hours}h, "
        f"re-analyzes after {settings.scheduler_interval_days} days"
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None


def get_status() -> dict:
    if _scheduler is None or not _scheduler.running:
        return {
            "running": False,
            "next_run": None,
            "interval_days": settings.scheduler_interval_days,
            "check_hours": settings.scheduler_check_hours,
            "enabled": settings.scheduler_enabled,
        }

    jobs = _scheduler.get_jobs()
    next_run = None
    if jobs and jobs[0].next_run_time:
        next_run = jobs[0].next_run_time.isoformat()

    return {
        "running": True,
        "next_run": next_run,
        "interval_days": settings.scheduler_interval_days,
        "check_hours": settings.scheduler_check_hours,
        "enabled": settings.scheduler_enabled,
    }
