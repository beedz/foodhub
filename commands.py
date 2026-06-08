"""Command handlers. Each returns a (success, message) tuple."""
from __future__ import annotations
import data as db

HELP_TEXT = """
[bold cyan]FoodHUD Commands[/bold cyan]

  [green]add[/green] <food> [quantity] [unit]
      Log a food item. Quantity defaults to 1. Unit defaults to the food's
      defined unit, or "item" if not yet defined.
      Examples:
        add banana
        add chicken 5 oz
        add oats 80 g

  [green]detail[/green] <food> <cal> <protein> <carbs> <fat> <fiber> [unit]
      Define nutritional info per 1 unit of a food.
      Unit defaults to "item" if omitted.
      Examples:
        detail banana 105 1.3 27 0.4 3.1
        detail chicken 55 6.9 0 2.4 0 oz
        detail oats 3.8 0.13 0.67 0.07 0.1 g

  [green]exercise[/green] <activity> <duration> [calories]
      Log exercise. Duration: 45min, 1hr, 1h30m. Calories optional — omit
      to auto-estimate based on activity type and your body weight.
      Examples:
        exercise run 45min
        exercise run 45min 400
        exercise bike 1hr

  [green]rmex[/green] <n>
      Remove exercise entry #n from today.

  [green]weight[/green] [lbs]
      View or set your body weight for exercise calorie estimates.

  [green]batch[/green]
      Enter multi-line input mode. Paste as many add/detail commands as you
      want (one per line), then hit Enter on a blank line to run them all.

  [green]edit[/green] <n>
      Edit the quantity or unit of the nth item in today's log.
      Prompts for new values, keeping current ones if you press Enter.

  [green]remove[/green] <n>
      Remove the nth item from today's log (1-based).

  [green]foods[/green]
      List all defined foods with their nutritional info.

  [green]goto[/green] <date>
      Time-travel to a past day. The whole HUD switches to it and every
      command (add/edit/remove/exercise) then operates on that day.
      Accepts: YYYY-MM-DD, yesterday, -N (N days ago). Type `today` to return.

  [green]today[/green]
      Return to today after using goto.

  [green]log[/green] [date]
      Show a single day's log table (defaults to the day you're viewing).

  [green]history[/green] [n | all | full [n]]
      Compact calorie overview, one line per day vs goal (default last 14).
        history 30    last 30 days
        history all   every day
        history full  detailed per-item tables (last 7)

  [green]help[/green]    Show this help.
  [green]quit[/green]    Exit FoodHUD.
"""


def cmd_add(args: list[str]) -> tuple[bool, str]:
    if not args:
        return False, "Usage: add <food> [quantity] [unit]"

    foods = db.get_foods()

    # Parse: food [quantity] [unit]
    # Heuristic: if last token is non-numeric and there are 3+ args → unit
    # if second token is numeric → quantity
    food = args[0].lower()
    quantity = 1.0
    unit: str | None = None

    if len(args) >= 2:
        try:
            quantity = float(args[1])
            if len(args) >= 3:
                unit = args[2].lower()
        except ValueError:
            # args[1] is not a number — treat whole remainder as food name
            food = " ".join(args).lower()

    if unit is None:
        defn = foods.get(food)
        unit = defn["unit"] if defn else "item"

    db.add_entry(food, quantity, unit)
    day_suffix = "" if db.is_viewing_today() else f" [dim]→ {_active_day_noun()}[/dim]"
    return True, f'Logged: {quantity:.1f} {unit} of "{food}"{day_suffix}'


def _prompt_field(label: str, default: float | None = None) -> float | None:
    """Prompt the user for a single numeric field. Returns None on blank+no default or invalid."""
    from rich.console import Console
    con = Console()
    hint = f" [dim](default: {default})[/dim]" if default is not None else ""
    while True:
        con.print(f"   [cyan]{label}[/cyan]{hint}: ", end="")
        raw = input().strip()
        if raw == "" and default is not None:
            return default
        if raw == "":
            return None
        try:
            return float(raw)
        except ValueError:
            con.print(f"   [red]Must be a number. Try again.[/red]")


def cmd_detail(args: list[str]) -> tuple[bool, str]:
    if not args:
        return False, "Usage: detail <food> [cal] [protein] [carbs] [fat] [fiber] [unit]"

    food = args[0].lower()

    # Inline mode: all values provided on one line
    if len(args) >= 6:
        try:
            cal = float(args[1])
            protein = float(args[2])
            carbs = float(args[3])
            fat = float(args[4])
            fiber = float(args[5])
        except ValueError:
            return False, "Nutritional values must be numbers."
        unit = args[6].lower() if len(args) >= 7 else "item"
        db.define_food(food, cal, protein, carbs, fat, fiber, unit)
        return True, f'Defined "{food}": {cal} kcal | {fat}g F | {carbs}g C | {fiber}g Fiber | {protein}g P  per {unit}'

    # Wizard mode: prompt for each field
    from rich.console import Console
    con = Console()
    existing = db.get_foods().get(food, {})

    con.print(f"\n [bold cyan]Detailing:[/bold cyan] [bold]{food}[/bold]  [dim](press Enter to keep existing value)[/dim]\n")

    fields = [
        ("Calories (kcal)", "calories"),
        ("Protein (g)", "protein"),
        ("Carbs (g)", "carbs"),
        ("Fat (g)", "fat"),
        ("Fiber (g)", "fiber"),
    ]

    values: dict[str, float] = {}
    for label, key in fields:
        default = existing.get(key)
        val = _prompt_field(label, default)
        if val is None:
            con.print(f"   [red]Cancelled — {label} is required.[/red]")
            return False, ""
        values[key] = val

    # Unit
    existing_unit = existing.get("unit", "item")
    con.print(f"   [cyan]Unit[/cyan] [dim](default: {existing_unit})[/dim]: ", end="")
    raw_unit = input().strip()
    unit = raw_unit.lower() if raw_unit else existing_unit

    db.define_food(food, values["calories"], values["protein"], values["carbs"], values["fat"], values["fiber"], unit)
    return True, (
        f'Defined "{food}": {values["calories"]} kcal | {values["fat"]}g F | '
        f'{values["carbs"]}g C | {values["fiber"]}g Fiber | {values["protein"]}g P  per {unit}'
    )


def cmd_edit(args: list[str]) -> tuple[bool, str]:
    if not args:
        return False, "Usage: edit <n>"
    try:
        n = int(args[0])
    except ValueError:
        return False, "Argument must be a number."

    entries = db.get_log()
    if n < 1 or n > len(entries):
        return False, f"No item #{n} in {_active_day_noun()}'s log."

    entry = entries[n - 1]
    from rich.console import Console
    con = Console(legacy_windows=False)
    con.print(f"\n [bold cyan]Editing #{n}:[/bold cyan] {entry['quantity']:.1f} {entry['unit']} x {entry['food']}\n")

    con.print(f"   [cyan]Quantity[/cyan] [dim](current: {entry['quantity']})[/dim]: ", end="")
    raw_qty = input().strip()
    if raw_qty:
        try:
            quantity = float(raw_qty)
        except ValueError:
            return False, "Quantity must be a number."
    else:
        quantity = entry["quantity"]

    con.print(f"   [cyan]Unit[/cyan] [dim](current: {entry['unit']})[/dim]: ", end="")
    raw_unit = input().strip()
    unit = raw_unit.lower() if raw_unit else entry["unit"]

    db.edit_entry(n, quantity, unit)
    return True, f'Updated #{n} "{entry["food"]}": {quantity:.1f} {unit}'


def cmd_remove(args: list[str]) -> tuple[bool, str]:
    if not args:
        return False, "Usage: remove <n>"
    try:
        n = int(args[0])
    except ValueError:
        return False, "Argument must be a number."
    if db.remove_entry(n):
        return True, f"Removed item #{n} from {_active_day_noun()}'s log."
    return False, f"No item #{n} in {_active_day_noun()}'s log."


def cmd_foods(_args: list[str]) -> tuple[bool, str]:
    foods = db.get_foods()
    if not foods:
        return True, "No foods defined yet. Use: detail <food> <cal> <protein> <carbs> <fat> [unit]"
    lines = ["[bold]Defined Foods:[/bold]"]
    for name, d in sorted(foods.items()):
        lines.append(
            f"  [cyan]{name}[/cyan] ({d['unit']}): "
            f"{d['calories']} kcal | {d['fat']}g F | {d['carbs']}g C | {d.get('fiber', 0)}g Fiber | {d['protein']}g P"
            f"  [dim]per 1 {d['unit']}[/dim]"
        )
    return True, "\n".join(lines)


def _print_day_block(day: str, entries: list, foods: dict, totals: dict) -> None:
    from datetime import date
    from rich.console import Console
    from rich.table import Table
    from rich import box

    con = Console(legacy_windows=False)

    try:
        label = date.fromisoformat(day).strftime("%A, %B %d, %Y").replace(" 0", " ")
    except ValueError:
        label = day

    con.print(f"\n [bold cyan]{label}[/bold cyan]  [dim]{day}[/dim]")

    # Pre-calculate calories per entry for data bar scaling
    CAL_BAR_WIDTH = 12
    entry_cals = []
    for e in entries:
        defn = foods.get(e["food"])
        entry_cals.append(round(defn["calories"] * e["quantity"]) if defn else None)
    max_cal = max((c for c in entry_cals if c is not None), default=1)

    def cal_bar(cal: int) -> str:
        filled = round((cal / max_cal) * CAL_BAR_WIDTH)
        return "█" * filled + "░" * (CAL_BAR_WIDTH - filled)

    t = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", pad_edge=False)
    t.add_column("#",       style="dim",          width=3,  justify="right")
    t.add_column("",        width=3)                          # icon
    t.add_column("Food",    style="bold",          min_width=14)
    t.add_column("Qty",     justify="right",       width=6)
    t.add_column("Unit",    style="dim",           width=6)
    t.add_column("Cal",     justify="right",       width=5,  style="green")
    t.add_column("",        width=CAL_BAR_WIDTH,             style="green")   # calorie bar
    t.add_column("Fat",     justify="right",       width=5,  style="red")
    t.add_column("Carbs",   justify="right",       width=6,  style="yellow")
    t.add_column("Fiber",   justify="right",       width=6,  style="magenta")
    t.add_column("Prot",    justify="right",       width=6,  style="blue")

    for i, (e, cal_val) in enumerate(zip(entries, entry_cals), 1):
        defn = foods.get(e["food"])
        if defn:
            icon = "[green]✓[/green]"
            q = e["quantity"]
            cal  = str(cal_val)
            bar  = cal_bar(cal_val)
            prot = str(round(defn["protein"]  * q, 1)) + "g"
            carb = str(round(defn["carbs"]    * q, 1)) + "g"
            fat  = str(round(defn["fat"]      * q, 1)) + "g"
            fib  = str(round(defn.get("fiber", 0) * q, 1)) + "g"
        else:
            icon = "[yellow]![/yellow]"
            cal = bar = prot = carb = fat = fib = "[dim]—[/dim]"

        t.add_row(str(i), icon, e["food"], f"{e['quantity']:.1f}", e["unit"],
                  cal, bar, fat, carb, fib, prot)

    # totals footer
    t.add_section()
    t.add_row(
        "", "", "[dim]Total[/dim]", "", "",
        f"[bold]{round(totals['calories'])}[/bold]",
        "",
        f"[bold]{round(totals['fat'],     1)}g[/bold]",
        f"[bold]{round(totals['carbs'],   1)}g[/bold]",
        f"[bold]{round(totals['fiber'],   1)}g[/bold]",
        f"[bold]{round(totals['protein'], 1)}g[/bold]",
    )

    con.print(t)


def cmd_batch(_args: list[str]) -> tuple[bool, str]:
    from rich.console import Console
    con = Console(legacy_windows=False)
    con.print("\n [bold cyan]Batch mode[/bold cyan]  [dim]Paste commands one per line. Blank line to run.[/dim]\n")

    lines = []
    while True:
        con.print("   [dim]>[/dim] ", end="")
        raw = input()
        if raw.strip() == "":
            break
        lines.append(raw.strip())

    if not lines:
        return True, "No commands entered."

    results = []
    errors = []
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        verb = parts[0].lower()
        args = parts[1:]
        handler = COMMANDS.get(verb)
        if handler is None:
            errors.append(f'Unknown command: "{verb}"')
        else:
            ok, msg = handler(args)
            if ok:
                results.append(f"[green]✓[/green] {msg}" if msg else f"[green]✓[/green] {line}")
            else:
                errors.append(f"[red]✗[/red] {line} — {msg}")

    summary = []
    summary.extend(results)
    summary.extend(errors)
    summary.append(f"\n[bold]{len(results)} logged[/bold], {len(errors)} errors")
    return True, "\n".join(summary)


def _day_label(day: str) -> str:
    """'Fri, Jun 5' style label for an ISO date string."""
    from datetime import date
    try:
        return date.fromisoformat(day).strftime("%a, %b %d").replace(" 0", " ")
    except ValueError:
        return day


def _active_day_noun() -> str:
    """'today' when viewing today, else 'Fri, Jun 5'."""
    return "today" if db.is_viewing_today() else _day_label(db.get_active_day())


def cmd_log(args: list[str]) -> tuple[bool, str]:
    day = db.parse_day(args[0]) if args else db.get_active_day()
    if day is None:
        return False, f'Could not parse date "{args[0]}". Try: 2026-06-05, today, yesterday, -1'
    entries = db.get_log(day)
    if not entries:
        return True, f"No entries for {_day_label(day)}."
    _print_day_block(day, entries, db.get_foods(), db.daily_totals(day))
    return True, ""


def _parse_duration(token: str) -> float | None:
    """Parse duration string into minutes. Accepts: 45, 45min, 45m, 1hr, 1h, 1h30m, 1h30."""
    import re
    token = token.lower().strip()
    # e.g. 1h30m or 1h30
    m = re.fullmatch(r'(\d+)h(\d+)m?', token)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    # e.g. 1hr, 1h
    m = re.fullmatch(r'(\d+(?:\.\d+)?)h(?:r|rs)?', token)
    if m:
        return float(m.group(1)) * 60
    # e.g. 45min, 45m, 45
    m = re.fullmatch(r'(\d+(?:\.\d+)?)(?:min|m)?', token)
    if m:
        return float(m.group(1))
    return None


def cmd_exercise(args: list[str]) -> tuple[bool, str]:
    if len(args) < 2:
        return False, "Usage: exercise <activity> <duration> [calories]\n  e.g. exercise run 45min  or  exercise run 45min 400"

    activity = args[0].lower()
    duration_min = _parse_duration(args[1])
    if duration_min is None:
        return False, f'Could not parse duration "{args[1]}". Try: 45min, 1hr, 1h30m'

    if len(args) >= 3:
        try:
            calories = int(args[2])
            estimated = False
        except ValueError:
            return False, "Calories must be a whole number."
    else:
        calories, estimated = db.estimate_calories_burned(activity, duration_min)

    db.add_exercise(activity, duration_min, calories, estimated)

    dur_str = f"{int(duration_min)}min" if duration_min == int(duration_min) else f"{duration_min}min"
    est_note = " [dim](estimated)[/dim]" if estimated else ""
    weight_note = f" [dim](based on {db.get_weight_lbs():.0f} lbs — use `weight <lbs>` to update)[/dim]" if estimated else ""
    day_suffix = "" if db.is_viewing_today() else f" [dim]→ {_active_day_noun()}[/dim]"
    return True, f"Logged: {activity} {dur_str} → {calories} kcal burned{est_note}{weight_note}{day_suffix}"


def cmd_remove_exercise(args: list[str]) -> tuple[bool, str]:
    if not args:
        return False, "Usage: rmex <n>"
    try:
        n = int(args[0])
    except ValueError:
        return False, "Argument must be a number."
    if db.remove_exercise(n):
        return True, f"Removed exercise #{n} from {_active_day_noun()}."
    return False, f"No exercise #{n} on {_active_day_noun()}."


def cmd_weight(args: list[str]) -> tuple[bool, str]:
    if not args:
        current = db.get_weight_lbs()
        return True, f"Current weight: {current:.0f} lbs. Use `weight <lbs>` to update."
    try:
        lbs = float(args[0])
    except ValueError:
        return False, "Weight must be a number (lbs)."
    db.set_weight_lbs(lbs)
    return True, f"Weight updated to {lbs:.0f} lbs. Exercise estimates will use this going forward."


def _print_history_compact(days: list[str]) -> None:
    from rich.console import Console
    from rich.text import Text
    con = Console(legacy_windows=False)

    BAR_W = 16
    base_goal = db.get_goals()["calories"]

    con.print(f"\n [bold]HISTORY[/bold]  [dim]({len(days)} day{'s' if len(days) != 1 else ''})[/dim]\n")

    for day in days:
        consumed = round(db.daily_totals(day)["calories"])
        burned = db.calories_burned_today(day)
        goal = round(base_goal + burned)
        pct = (consumed / goal) if goal else 0
        filled = min(round(pct * BAR_W), BAR_W)
        over = consumed > goal
        bar_color = "red" if over else "green"
        bar = "█" * filled + "░" * (BAR_W - filled)

        label = _day_label(day)
        is_active = day == db.get_active_day()

        line = Text()
        line.append(" ● " if is_active else "   ", style="yellow")
        line.append(f"{label:<11}", style="bold" if day == db.today() else "white")
        line.append(f"{consumed:>5} / {goal:<5} ", style="dim")
        line.append("[", style="dim")
        line.append(bar, style=bar_color)
        line.append("] ", style="dim")
        line.append(f"{int(pct*100):>3}%", style=bar_color if over else "white")
        if over:
            line.append("  over", style="red")
        if burned:
            line.append(f"   🏃 +{burned}", style="cyan")
        con.print(line)
    con.print()


def cmd_history(args: list[str]) -> tuple[bool, str]:
    days = db.get_all_days()
    if not days:
        return True, "No history yet."

    # Detailed mode: `history full [n]`
    if args and args[0].lower() == "full":
        n = 7
        if len(args) >= 2 and args[1].isdigit():
            n = int(args[1])
        from rich.console import Console
        con = Console(legacy_windows=False)
        con.print(f"\n [bold]Full History[/bold]  [dim](last {min(n, len(days))} days)[/dim]")
        foods = db.get_foods()
        for day in days[:n]:
            _print_day_block(day, db.get_log(day), foods, db.daily_totals(day))
        return True, ""

    # Compact mode: default 14, `history N`, or `history all`
    if args and args[0].lower() == "all":
        selected = days
    elif args and args[0].isdigit():
        selected = days[:int(args[0])]
    else:
        selected = days[:14]

    _print_history_compact(selected)
    return True, ""


def cmd_goto(args: list[str]) -> tuple[bool, str]:
    if not args:
        db.set_active_day(None)
        return True, "Now viewing today."
    day = db.parse_day(args[0])
    if day is None:
        return False, f'Could not parse date "{args[0]}". Try: 2026-06-05, today, yesterday, -1'
    if day == db.today():
        db.set_active_day(None)
        return True, "Now viewing today."
    db.set_active_day(day)
    return True, f"Now viewing {_day_label(day)} — type 'today' to return."


def cmd_today(_args: list[str]) -> tuple[bool, str]:
    db.set_active_day(None)
    return True, "Now viewing today."


COMMANDS = {
    "add": cmd_add,
    "detail": cmd_detail,
    "edit": cmd_edit,
    "remove": cmd_remove,
    "rm": cmd_remove,
    "batch": cmd_batch,
    "exercise": cmd_exercise,
    "rmex": cmd_remove_exercise,
    "weight": cmd_weight,
    "goto": cmd_goto,
    "today": cmd_today,
    "foods": cmd_foods,
    "log": cmd_log,
    "history": cmd_history,
    "help": lambda _: (True, HELP_TEXT),
    "?": lambda _: (True, HELP_TEXT),
}
