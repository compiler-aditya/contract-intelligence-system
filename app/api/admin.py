"""Admin and monitoring endpoints"""
from fastapi import APIRouter, Request
from datetime import datetime
import time
import psutil
from typing import Dict, Any

router = APIRouter()

# Metrics storage (in production, use Prometheus or similar)
metrics: Dict[str, int] = {
    "documents_ingested": 0,
    "extractions_performed": 0,
    "questions_asked": 0,
    "audits_completed": 0,
    "api_requests": 0,
    "errors": 0,
}


def increment_metric(metric_name: str, amount: int = 1):
    """Increment a metric counter"""
    if metric_name in metrics:
        metrics[metric_name] += amount


@router.get("/healthz")
async def health_check(request: Request):
    """
    Health check endpoint
    Returns the health status of the application
    """
    try:
        # Calculate uptime
        startup_time = getattr(request.app.state, 'startup_time', time.time())
        uptime_seconds = int(time.time() - startup_time)

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime_seconds,
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // (1024 * 1024),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free // (1024 * 1024 * 1024)
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/metrics")
async def get_metrics(request: Request):
    """
    Get application metrics
    Returns counters for various operations and system info
    """
    # Calculate uptime
    startup_time = getattr(request.app.state, 'startup_time', time.time())
    uptime_seconds = int(time.time() - startup_time)

    # Calculate rates
    requests_per_minute = (
        metrics["api_requests"] / max(uptime_seconds / 60, 1)
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": uptime_seconds,
        "counters": metrics,
        "rates": {
            "requests_per_minute": round(requests_per_minute, 2),
            "error_rate": round(
                metrics["errors"] / max(metrics["api_requests"], 1) * 100, 2
            )
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "process_memory_mb": psutil.Process().memory_info().rss // (1024 * 1024)
        }
    }


@router.post("/metrics/reset")
async def reset_metrics():
    """
    Reset all metrics counters
    Useful for testing or starting fresh
    """
    global metrics
    for key in metrics:
        metrics[key] = 0

    return {
        "message": "Metrics reset successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics/prometheus")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint
    Returns metrics in Prometheus text format
    """
    lines = [
        "# HELP documents_ingested Total number of documents ingested",
        "# TYPE documents_ingested counter",
        f"documents_ingested {metrics['documents_ingested']}",
        "",
        "# HELP extractions_performed Total number of extractions performed",
        "# TYPE extractions_performed counter",
        f"extractions_performed {metrics['extractions_performed']}",
        "",
        "# HELP questions_asked Total number of questions asked",
        "# TYPE questions_asked counter",
        f"questions_asked {metrics['questions_asked']}",
        "",
        "# HELP audits_completed Total number of audits completed",
        "# TYPE audits_completed counter",
        f"audits_completed {metrics['audits_completed']}",
        "",
        "# HELP api_requests Total number of API requests",
        "# TYPE api_requests counter",
        f"api_requests {metrics['api_requests']}",
        "",
        "# HELP errors Total number of errors",
        "# TYPE errors counter",
        f"errors {metrics['errors']}",
        "",
        "# HELP cpu_percent CPU usage percentage",
        "# TYPE cpu_percent gauge",
        f"cpu_percent {psutil.cpu_percent(interval=0.1)}",
        "",
        "# HELP memory_percent Memory usage percentage",
        "# TYPE memory_percent gauge",
        f"memory_percent {psutil.virtual_memory().percent}",
    ]

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("\n".join(lines))
