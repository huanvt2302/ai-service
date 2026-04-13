"""
Burst Controller — GCP Cloud Run Auto-Scaler
============================================

This daemon runs on the Swarm Manager node. It polls Prometheus every
POLL_INTERVAL seconds and calls `gcloud run services update` to warm up or
scale down Cloud Run services based on aggregate local cluster CPU.

Behaviour:
  - CPU rises above BURST_THRESHOLD for BURST_CONFIRM_SECS
      → scale Cloud Run min-instances to BURST_MIN_INSTANCES
        (so at least one instance is warm and ready)
  - CPU falls below SCALE_DOWN_THRESHOLD for SCALE_DOWN_SECS
      → scale Cloud Run min-instances back to 0 (zero cost when idle)

Environment variables:
  PROMETHEUS_URL          (default: http://prometheus:9090)
  GCP_PROJECT             GCP project ID
  GCP_REGION              Cloud Run region           (default: asia-southeast1)
  CLOUD_RUN_SERVICES      Comma-separated svc names  (default: ai-backend,ai-vllm)
  BURST_THRESHOLD         CPU % trigger              (default: 70)
  SCALE_DOWN_THRESHOLD    CPU % to scale down        (default: 40)
  BURST_MIN_INSTANCES     min-instances when bursting (default: 2)
  POLL_INTERVAL           Seconds between polls      (default: 10)
  BURST_CONFIRM_SECS      Seconds CPU must be high   (default: 30)
  SCALE_DOWN_SECS         Seconds CPU must be low    (default: 60)

Requires `gcloud` CLI authenticated with a Service Account that has:
  - roles/run.admin  (to update Cloud Run services)
"""

import asyncio
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

# ── Configuration ──────────────────────────────────────────────────────────────

PROMETHEUS_URL         = os.getenv("PROMETHEUS_URL",         "http://prometheus:9090")
GCP_PROJECT            = os.getenv("GCP_PROJECT",            "")
GCP_REGION             = os.getenv("GCP_REGION",             "asia-southeast1")
CLOUD_RUN_SERVICES     = os.getenv("CLOUD_RUN_SERVICES",     "ai-backend,ai-vllm").split(",")
BURST_THRESHOLD        = float(os.getenv("BURST_THRESHOLD",         "70"))
SCALE_DOWN_THRESHOLD   = float(os.getenv("SCALE_DOWN_THRESHOLD",    "40"))
BURST_MIN_INSTANCES    = int(os.getenv("BURST_MIN_INSTANCES",        "2"))
POLL_INTERVAL          = int(os.getenv("POLL_INTERVAL",              "10"))
BURST_CONFIRM_SECS     = int(os.getenv("BURST_CONFIRM_SECS",         "30"))
SCALE_DOWN_SECS        = int(os.getenv("SCALE_DOWN_SECS",            "60"))


# ── Logging ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level   = logging.INFO,
    stream  = sys.stdout,
    format  = "%(asctime)s [%(levelname)s] burst-controller — %(message)s",
    datefmt = "%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("burst-controller")


# ── GCloud helpers ─────────────────────────────────────────────────────────────

def _gcloud_update_min_instances(service: str, n: int) -> bool:
    """
    Calls `gcloud run services update <service> --min-instances=<n>`.
    Returns True on success, False on failure.
    """
    cmd = [
        "gcloud", "run", "services", "update", service,
        f"--project={GCP_PROJECT}",
        f"--region={GCP_REGION}",
        f"--min-instances={n}",
        "--quiet",          # suppress interactive prompts
        "--format=none",    # no output on success
    ]
    log.info("$ %s", " ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        log.error(
            "gcloud failed for service=%s: %s",
            service, result.stderr.strip() or result.stdout.strip()
        )
        return False

    log.info("OK: service=%s min-instances=%d", service, n)
    return True


def scale_cloud_run(min_instances: int):
    """Scale all configured Cloud Run services to the target min-instances."""
    if not GCP_PROJECT:
        log.warning("GCP_PROJECT not set — skipping Cloud Run scaling")
        return

    for svc in CLOUD_RUN_SERVICES:
        svc = svc.strip()
        if svc:
            _gcloud_update_min_instances(svc, min_instances)


# ── Prometheus helpers ─────────────────────────────────────────────────────────

async def fetch_cluster_cpu() -> float:
    """
    Query Prometheus for the average CPU usage across all cluster nodes
    (reported by node_exporter running in global Swarm mode).

    Returns 0.0 on any error — the controller will not burst if Prometheus
    is unreachable (fail-safe).
    """
    promql = (
        '100 - avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100'
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": promql},
            )
            data    = resp.json()
            results = data.get("data", {}).get("result", [])
            if not results:
                log.warning("Prometheus returned no CPU results")
                return 0.0
            return float(results[0]["value"][1])

    except Exception as exc:
        log.warning("Cannot reach Prometheus: %s — defaulting to 0%%", exc)
        return 0.0


# ── Controller State Machine ───────────────────────────────────────────────────

@dataclass
class ControllerState:
    is_bursting:     bool          = False
    high_cpu_since:  Optional[float] = None   # monotonic time
    low_cpu_since:   Optional[float] = None   # monotonic time
    last_action_at:  Optional[float] = None


async def run_controller():
    state = ControllerState()
    log.info(
        "Started. poll=%ds burst_threshold=%.0f%% scale_down_threshold=%.0f%% "
        "burst_confirm=%ds scale_down=%ds services=%s",
        POLL_INTERVAL, BURST_THRESHOLD, SCALE_DOWN_THRESHOLD,
        BURST_CONFIRM_SECS, SCALE_DOWN_SECS, CLOUD_RUN_SERVICES,
    )

    while True:
        try:
            cpu = await fetch_cluster_cpu()
            now = time.monotonic()

            log.info(
                "CPU=%.1f%% | bursting=%s | high_since=%.0fs | low_since=%.0fs",
                cpu,
                state.is_bursting,
                (now - state.high_cpu_since) if state.high_cpu_since else 0,
                (now - state.low_cpu_since)  if state.low_cpu_since  else 0,
            )

            # ── Scale UP path ──────────────────────────────────────────────────
            if cpu >= BURST_THRESHOLD:
                state.low_cpu_since = None   # reset scale-down timer

                if state.high_cpu_since is None:
                    state.high_cpu_since = now
                    log.info("CPU crossed BURST threshold (%.1f%% >= %.0f%%) — starting confirmation timer",
                             cpu, BURST_THRESHOLD)

                elif not state.is_bursting:
                    elapsed = now - state.high_cpu_since
                    remaining = BURST_CONFIRM_SECS - elapsed
                    if remaining <= 0:
                        log.warning(
                            "CPU has been high for %ds → BURST UP (min-instances=%d)",
                            BURST_CONFIRM_SECS, BURST_MIN_INSTANCES,
                        )
                        scale_cloud_run(BURST_MIN_INSTANCES)
                        state.is_bursting    = True
                        state.last_action_at = now
                    else:
                        log.info("Confirming burst in %.0fs…", remaining)

            # ── Scale DOWN path ────────────────────────────────────────────────
            elif cpu < SCALE_DOWN_THRESHOLD and state.is_bursting:
                state.high_cpu_since = None  # reset burst timer

                if state.low_cpu_since is None:
                    state.low_cpu_since = now
                    log.info("CPU dropped below scale-down threshold (%.1f%% < %.0f%%) — starting cool-down timer",
                             cpu, SCALE_DOWN_THRESHOLD)

                else:
                    elapsed   = now - state.low_cpu_since
                    remaining = SCALE_DOWN_SECS - elapsed
                    if remaining <= 0:
                        log.info(
                            "CPU has been low for %ds → SCALE DOWN (min-instances=0)",
                            SCALE_DOWN_SECS,
                        )
                        scale_cloud_run(0)
                        state.is_bursting    = False
                        state.low_cpu_since  = None
                        state.last_action_at = now
                    else:
                        log.info("Scaling down in %.0fs…", remaining)

            # ── Normal state (CPU between thresholds or falling) ───────────────
            else:
                if cpu < BURST_THRESHOLD:
                    state.high_cpu_since = None   # reset burst timer if CPU recovered below burst but above scale-down

        except Exception as exc:
            log.error("Unexpected error in control loop: %s", exc, exc_info=True)

        await asyncio.sleep(POLL_INTERVAL)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run_controller())
