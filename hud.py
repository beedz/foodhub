from datetime import date
import shutil

from rich.console import Console
from rich.text import Text

import data as db

console = Console(legacy_windows=False)

BAR_WIDTH = 38   # inner fill chars between [ ]
COL_WIDTH = 80   # max HUD width


def _term_width() -> int:
    return min(shutil.get_terminal_size().columns, COL_WIDTH)


def _bar(value: float, goal: float) -> tuple[str, float]:
    """Return (bar_string, pct) — bar_string is plain text with block chars."""
    pct = min(value / goal, 1.0) if goal > 0 else 0.0
    filled = round(pct * BAR_WIDTH)
    return "█" * filled + "░" * (BAR_WIDTH - filled), pct


def _cal_color(pct: float) -> str:
    if pct >= 1.0:
        return "bold red"
    if pct >= 0.85:
        return "bold yellow"
    return "bold green"


def _render_bar_line(
    label: str,
    value: float,
    goal: float,
    unit: str,
    color: str,
    label_w: int = 10,
    num_w: int = 4,
) -> None:
    bar, pct = _bar(value, goal)
    pct_str = f"({int(pct * 100):3d}%)"
    val_str  = f"{round(value):>{num_w}}"
    goal_str = f"{round(goal):>{num_w}}"
    label_str = label.ljust(label_w)

    line = Text()
    line.append(f"  {label_str} [", style="dim white")
    line.append(bar, style=color)
    line.append("]  ", style="dim white")
    line.append(f"{val_str} / {goal_str} {unit}  ", style="white")
    line.append(pct_str, style="dim")
    console.print(line)


def render() -> None:
    console.clear()
    W = _term_width()
    div_eq = "=" * W
    div_dash = "-" * W

    active_day = db.get_active_day()
    viewing_today = db.is_viewing_today()
    day_obj = date.fromisoformat(active_day)
    day_str = day_obj.strftime("%A, %B %d, %Y").replace(" 0", " ")
    short_day = day_obj.strftime("%a, %b %d").replace(" 0", " ")

    # ── Header ──────────────────────────────────────────────────────────────
    console.print(div_eq, style="bold cyan")
    title = f" FOODHUD (fh)  |  {day_str}"
    status = "[Active]"
    gap = W - len(title) - len(status) - 1
    console.print(title + " " * max(gap, 1) + status, style="bold cyan")
    if not viewing_today:
        banner = f" ⏪ VIEWING PAST DAY — type 'today' to return"
        console.print(banner, style="bold yellow")
    console.print(div_eq, style="bold cyan")

    # ── Attention Required ───────────────────────────────────────────────────
    entries = db.get_log()
    foods = db.get_foods()
    undetailed: dict[str, str] = {}
    for e in entries:
        if e["food"] not in foods and e["food"] not in undetailed:
            undetailed[e["food"]] = e["unit"]

    if undetailed:
        console.print(" [bold yellow]⚠  ATTENTION REQUIRED:[/bold yellow]")
        for name, unit in undetailed.items():
            console.print(f'   - [yellow]"{name}"[/yellow] needs details! (Tracked in: {unit})')
        console.print()

    # ── Exercise ─────────────────────────────────────────────────────────────
    exercise_entries = db.get_exercise()
    burned = db.calories_burned_today()
    if exercise_entries:
        console.print(div_dash, style="dim")
        ex_title = "TODAY'S EXERCISE:" if viewing_today else f"EXERCISE — {short_day}:"
        console.print(f" [bold]{ex_title}[/bold]")
        for i, ex in enumerate(exercise_entries, 1):
            dur = int(ex["duration_min"])
            est = " [dim](est)[/dim]" if ex.get("estimated") else ""
            console.print(f"   [dim]{i:>2}.[/dim]  [cyan]{ex['activity']}[/cyan]  {dur} min  →  [green]{ex['calories']} kcal burned[/green]{est}")
        console.print()

    # ── Nutrition Bars ───────────────────────────────────────────────────────
    console.print(div_dash, style="dim")
    totals = db.daily_totals()
    goals = db.get_goals()
    cal_goal = goals["calories"] + burned
    goal_label = "estimated from detailed items"
    if burned:
        goal_label += f"  [green]+{burned} kcal from exercise[/green]"
    console.print(f" [bold]DAILY NUTRITION[/bold]  [dim]{goal_label}[/dim]")
    console.print()

    cal_pct = totals["calories"] / cal_goal if cal_goal else 0
    _render_bar_line("CALORIES", totals["calories"], cal_goal, "kcal", _cal_color(cal_pct), num_w=4)
    console.print()
    _render_bar_line("FAT",      totals["fat"],      goals["fat"],      "g",    "bold red")
    _render_bar_line("CARBS",    totals["carbs"],    goals["carbs"],    "g",    "bold yellow")
    _render_bar_line("FIBER",    totals["fiber"],    goals["fiber"],    "g",    "bold magenta")
    _render_bar_line("PROTEIN",  totals["protein"],  goals["protein"],  "g",    "bold blue")
    console.print()

    # ── Log ──────────────────────────────────────────────────────────────────
    console.print(div_dash, style="dim")
    log_title = "TODAY'S LOG:" if viewing_today else f"LOG — {short_day}:"
    console.print(f" [bold]{log_title}[/bold]")
    if not entries:
        console.print("   [dim](nothing logged yet)[/dim]")
    else:
        for i, e in enumerate(entries, 1):
            is_detailed = e["food"] in foods
            icon = "[green][✓][/green]" if is_detailed else "[yellow][!][/yellow]"
            qty = f"{e['quantity']:.1f}"
            unit_str = e["unit"].ljust(6)
            num = f"[dim]{i:>2}.[/dim]"
            console.print(f"   {num} {icon} {qty} {unit_str} x  {e['food']}")
    console.print(div_eq, style="bold cyan")
