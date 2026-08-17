"""
PortConnect API client for scheduled vessels (real NZ port data).
PortConnect 船舶时刻表 API 客户端（新西兰港口真实数据）

Endpoint: GET https://api.portconnect.io/v1/scheduled-vessels
Optional param: portCode (NZAKL, NZTRG, NZWLG, NZLYT, NZTIU)

Falls back to a local snapshot (scheduled_vessels_full.json) when the API is
unreachable (offline / rate-limited / tests), so the simulator keeps working.
"""
import json
import os
import requests

from config import settings

API_BASE = "https://api.portconnect.io/v1"
LOCAL_SNAPSHOT = os.path.join(os.path.dirname(__file__), "scheduled_vessels_full.json")

NZ_PORT_CODES = ["NZAKL", "NZTRG", "NZWLG", "NZLYT", "NZTIU"]


def _headers():
    return {
        "Ocp-Apim-Subscription-Key": settings.portconnect_api_key,
        "Content-Type": "application/json",
    }


def fetch_scheduled_vessels(port_code=None, timeout=20):
    """
    Fetch real scheduled vessels from PortConnect API.

    Args:
        port_code: Optional port filter (e.g. 'NZAKL')
        timeout: Request timeout in seconds

    Returns:
        List of vessel visit dicts, or None on failure
    """
    if not settings.portconnect_api_enabled:
        return None
    url = f"{API_BASE}/scheduled-vessels"
    params = {"portCode": port_code} if port_code else {}
    try:
        response = requests.get(url, headers=_headers(), params=params, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
    except requests.exceptions.RequestException as e:
        print(f"[portconnect] API error: {e}")
    return None


def fetch_all_scheduled_vessels():
    """Fetch scheduled vessels for all NZ ports, falling back to the local snapshot."""
    results = []
    if settings.portconnect_api_enabled:
        for port in NZ_PORT_CODES:
            data = fetch_scheduled_vessels(port_code=port)
            if data:
                results.extend(data)
    if results:
        return results
    return load_local_snapshot()


def load_local_snapshot():
    """Load the local scheduled-vessels snapshot (offline fallback)."""
    try:
        with open(LOCAL_SNAPSHOT, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            print(f"[portconnect] loaded {len(data)} vessel visits from local snapshot")
            return data
    except (OSError, json.JSONDecodeError) as e:
        print(f"[portconnect] local snapshot unavailable: {e}")
    return []


def get_vessels(port_code=None):
    """
    Get scheduled vessels, preferring live API then local snapshot.

    Returns:
        List of vessel visit dicts
    """
    data = fetch_scheduled_vessels(port_code=port_code) if port_code else fetch_all_scheduled_vessels()
    if data is None:
        data = load_local_snapshot()
        if port_code:
            data = [d for d in data if d.get("portCode") == port_code]
    return data
