import json
import os
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path.home() / ".foodhub"
DATA_FILE = DATA_DIR / "data.json"

DEFAULT_DOC = {"foods": {}, "log": {}}

# ── Storage backend ───────────────────────────────────────────────────────────
# If FOODHUB_API_URL is set, the TUI talks to a remote server (online-only mode);
# otherwise it reads/writes the local JSON file exactly as before. The whole app
# funnels through _load()/_save(), so this is the only place that changes.
API_URL = os.environ.get("FOODHUB_API_URL")
API_TOKEN = os.environ.get("FOODHUB_TOKEN")

# Per-render document cache: a single HUD render calls _load() many times. We cache
# the document and let the REPL call refresh() once per loop, so each render performs
# exactly one network fetch. Mutations write through and keep the cache warm.
_cache: dict | None = None


def is_remote() -> bool:
    return bool(API_URL)


def refresh() -> None:
    """Drop the cached document so the next _load() re-fetches. Called once per REPL loop."""
    global _cache
    _cache = None


def _remote_request(method: str, path: str, payload: dict | None = None) -> dict:
    url = API_URL.rstrip("/") + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {API_TOKEN}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Server error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot reach FoodHUD server at {API_URL}: {e.reason}") from e


def _fetch_doc() -> dict:
    if is_remote():
        return _remote_request("GET", "/data").get("doc", dict(DEFAULT_DOC))
    if not DATA_FILE.exists():
        return dict(DEFAULT_DOC)
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _store_doc(doc: dict) -> None:
    if is_remote():
        _remote_request("PUT", "/data", doc)
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(doc, f, indent=2)

# ── Active day (ephemeral, session-only) ──────────────────────────────────────
# When the user "goes to" a past day, all reads/writes target it until reset.
_active_day: str | None = None


def get_active_day() -> str:
    return _active_day or today()


def set_active_day(day: str | None) -> None:
    global _active_day
    _active_day = day


def is_viewing_today() -> bool:
    return get_active_day() == today()


def parse_day(token: str) -> str | None:
    """Parse a day token into an ISO date string, or None if unparseable.
    Accepts: 'today', 'yesterday', 'YYYY-MM-DD', and '-N' (N days ago)."""
    token = token.strip().lower()
    if token in ("today", ""):
        return today()
    if token == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    if token.startswith("-") and token[1:].isdigit():
        return (date.today() - timedelta(days=int(token[1:]))).isoformat()
    try:
        return date.fromisoformat(token).isoformat()
    except ValueError:
        return None


def _load() -> dict:
    """Return the FoodHUD document, using the per-render cache when available."""
    global _cache
    if _cache is None:
        _cache = _fetch_doc()
    return _cache


def _save(data: dict) -> None:
    """Persist the document (local file or remote server) and keep the cache warm."""
    global _cache
    _store_doc(data)
    _cache = data


def today() -> str:
    return date.today().isoformat()


def get_foods() -> dict:
    return _load()["foods"]


def get_log(day: str | None = None) -> list:
    data = _load()
    return data["log"].get(day or get_active_day(), [])


def add_entry(food: str, quantity: float, unit: str) -> None:
    data = _load()
    key = get_active_day()
    data["log"].setdefault(key, [])
    data["log"][key].append({"food": food, "quantity": quantity, "unit": unit})
    _save(data)


def edit_entry(index: int, quantity: float, unit: str) -> bool:
    """Update quantity/unit of a 1-based index in the active day's log. Returns True if updated."""
    data = _load()
    key = get_active_day()
    entries = data["log"].get(key, [])
    if index < 1 or index > len(entries):
        return False
    entries[index - 1]["quantity"] = quantity
    entries[index - 1]["unit"] = unit
    data["log"][key] = entries
    _save(data)
    return True


def get_all_days() -> list[str]:
    """Return all dates with food or exercise entries, sorted descending."""
    data = _load()
    days = set(data["log"].keys()) | set(data.get("exercise", {}).keys())
    return sorted(days, reverse=True)


def remove_entry(index: int) -> bool:
    """Remove 1-based index from the active day's log. Returns True if removed."""
    data = _load()
    key = get_active_day()
    entries = data["log"].get(key, [])
    if index < 1 or index > len(entries):
        return False
    entries.pop(index - 1)
    data["log"][key] = entries
    _save(data)
    return True


def define_food(name: str, calories: float, protein: float, carbs: float, fat: float, fiber: float, unit: str) -> None:
    data = _load()
    data["foods"][name.lower()] = {
        "unit": unit,
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "fiber": fiber,
    }
    _save(data)


def daily_totals(day: str | None = None) -> dict:
    """Returns {calories, protein, carbs, fat} for detailed items only."""
    foods = get_foods()
    entries = get_log(day or get_active_day())
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0}
    for entry in entries:
        defn = foods.get(entry["food"])
        if defn:
            q = entry["quantity"]
            totals["calories"] += defn["calories"] * q
            totals["protein"] += defn["protein"] * q
            totals["carbs"] += defn["carbs"] * q
            totals["fat"] += defn["fat"] * q
            totals["fiber"] += defn.get("fiber", 0.0) * q
    return totals


# MET values (Metabolic Equivalent of Task) by activity keyword
MET_TABLE = {
    "run": 9.8, "running": 9.8, "jog": 7.0, "jogging": 7.0,
    "walk": 3.5, "walking": 3.5,
    "bike": 7.5, "biking": 7.5, "cycling": 7.5, "cycle": 7.5,
    "swim": 8.0, "swimming": 8.0,
    "weights": 3.5, "lifting": 3.5, "weightlifting": 3.5,
    "hiit": 8.0,
    "yoga": 2.5,
    "elliptical": 5.0,
    "basketball": 8.0,
    "soccer": 7.0,
    "tennis": 7.3,
    "rowing": 7.0,
    "hike": 5.3, "hiking": 5.3,
}
DEFAULT_MET = 5.0
DEFAULT_WEIGHT_LBS = 155.0


def get_weight_lbs() -> float:
    data = _load()
    return data.get("settings", {}).get("weight_lbs", DEFAULT_WEIGHT_LBS)


def set_weight_lbs(lbs: float) -> None:
    data = _load()
    data.setdefault("settings", {})["weight_lbs"] = lbs
    _save(data)


def estimate_calories_burned(activity: str, duration_min: float) -> tuple[int, bool]:
    """Returns (calories_burned, was_estimated). Uses MET × weight × hours."""
    met = MET_TABLE.get(activity.lower(), DEFAULT_MET)
    weight_kg = get_weight_lbs() * 0.453592
    calories = met * weight_kg * (duration_min / 60)
    return round(calories), True


def add_exercise(activity: str, duration_min: float, calories: int, estimated: bool) -> None:
    data = _load()
    key = get_active_day()
    data.setdefault("exercise", {}).setdefault(key, [])
    data["exercise"][key].append({
        "activity": activity,
        "duration_min": duration_min,
        "calories": calories,
        "estimated": estimated,
    })
    _save(data)


def get_exercise(day: str | None = None) -> list:
    data = _load()
    return data.get("exercise", {}).get(day or get_active_day(), [])


def remove_exercise(index: int) -> bool:
    data = _load()
    key = get_active_day()
    entries = data.get("exercise", {}).get(key, [])
    if index < 1 or index > len(entries):
        return False
    entries.pop(index - 1)
    data["exercise"][key] = entries
    _save(data)
    return True


def calories_burned_today(day: str | None = None) -> int:
    return sum(e["calories"] for e in get_exercise(day or get_active_day()))


DEFAULT_GOALS = {
    "calories": 2000.0,
    "protein": 150.0,
    "carbs": 250.0,
    "fat": 65.0,
    "fiber": 30.0,
}


def get_goals() -> dict:
    data = _load()
    return {**DEFAULT_GOALS, **data.get("goals", {})}


def needs_detail(entry: dict) -> bool:
    foods = get_foods()
    return entry["food"] not in foods
