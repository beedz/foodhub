import json
import os
from datetime import date
from pathlib import Path

DATA_DIR = Path.home() / ".foodhub"
DATA_FILE = DATA_DIR / "data.json"


def _load() -> dict:
    if not DATA_FILE.exists():
        return {"foods": {}, "log": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def today() -> str:
    return date.today().isoformat()


def get_foods() -> dict:
    return _load()["foods"]


def get_log(day: str | None = None) -> list:
    data = _load()
    return data["log"].get(day or today(), [])


def add_entry(food: str, quantity: float, unit: str) -> None:
    data = _load()
    key = today()
    data["log"].setdefault(key, [])
    data["log"][key].append({"food": food, "quantity": quantity, "unit": unit})
    _save(data)


def edit_entry(index: int, quantity: float, unit: str) -> bool:
    """Update quantity/unit of a 1-based index in today's log. Returns True if updated."""
    data = _load()
    key = today()
    entries = data["log"].get(key, [])
    if index < 1 or index > len(entries):
        return False
    entries[index - 1]["quantity"] = quantity
    entries[index - 1]["unit"] = unit
    data["log"][key] = entries
    _save(data)
    return True


def get_all_days() -> list[str]:
    """Return all logged dates sorted descending."""
    data = _load()
    return sorted(data["log"].keys(), reverse=True)


def remove_entry(index: int) -> bool:
    """Remove 1-based index from today's log. Returns True if removed."""
    data = _load()
    key = today()
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
    entries = get_log(day)
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
