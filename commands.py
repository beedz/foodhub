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

  [green]edit[/green] <n>
      Edit the quantity or unit of the nth item in today's log.
      Prompts for new values, keeping current ones if you press Enter.

  [green]remove[/green] <n>
      Remove the nth item from today's log (1-based).

  [green]foods[/green]
      List all defined foods with their nutritional info.

  [green]log[/green] [date]
      Show today's log (or a specific date: YYYY-MM-DD).

  [green]history[/green]
      Show every day you've logged, with entries and totals.

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
    return True, f'Logged: {quantity:.1f} {unit} of "{food}"'


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
        return False, f"No item #{n} in today's log."

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
        return True, f"Removed item #{n} from today's log."
    return False, f"No item #{n} in today's log."


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

    t = Table(box=box.SIMPLE, show_header=True, header_style="bold dim", pad_edge=False)
    t.add_column("#",       style="dim",          width=3,  justify="right")
    t.add_column("",        width=3)                          # icon
    t.add_column("Food",    style="bold",          min_width=14)
    t.add_column("Qty",     justify="right",       width=6)
    t.add_column("Unit",    style="dim",           width=6)
    t.add_column("Cal",     justify="right",       width=5,  style="green")
    t.add_column("Fat",     justify="right",       width=5,  style="red")
    t.add_column("Carbs",   justify="right",       width=6,  style="yellow")
    t.add_column("Fiber",   justify="right",       width=6,  style="magenta")
    t.add_column("Prot",    justify="right",       width=6,  style="blue")

    for i, e in enumerate(entries, 1):
        defn = foods.get(e["food"])
        if defn:
            icon = "[green]✓[/green]"
            q = e["quantity"]
            cal  = str(round(defn["calories"] * q))
            prot = str(round(defn["protein"]  * q, 1)) + "g"
            carb = str(round(defn["carbs"]    * q, 1)) + "g"
            fat  = str(round(defn["fat"]      * q, 1)) + "g"
            fib  = str(round(defn.get("fiber", 0) * q, 1)) + "g"
        else:
            icon = "[yellow]![/yellow]"
            cal = prot = carb = fat = fib = "[dim]—[/dim]"

        t.add_row(str(i), icon, e["food"], f"{e['quantity']:.1f}", e["unit"],
                  cal, fat, carb, fib, prot)

    # totals footer
    t.add_section()
    t.add_row(
        "", "", "[dim]Total[/dim]", "", "",
        f"[bold]{round(totals['calories'])}[/bold]",
        f"[bold]{round(totals['fat'],     1)}g[/bold]",
        f"[bold]{round(totals['carbs'],   1)}g[/bold]",
        f"[bold]{round(totals['fiber'],   1)}g[/bold]",
        f"[bold]{round(totals['protein'], 1)}g[/bold]",
    )

    con.print(t)


def cmd_log(args: list[str]) -> tuple[bool, str]:
    day = args[0] if args else db.today()
    entries = db.get_log(day)
    if not entries:
        return True, f"No entries for {day}."
    _print_day_block(day, entries, db.get_foods(), db.daily_totals(day))
    return True, ""


def cmd_history(_args: list[str]) -> tuple[bool, str]:
    days = db.get_all_days()
    if not days:
        return True, "No history yet."
    from rich.console import Console
    con = Console(legacy_windows=False)
    con.print(f"\n [bold]Full History[/bold]  [dim]({len(days)} day{'s' if len(days) != 1 else ''})[/dim]")
    foods = db.get_foods()
    for day in days:
        _print_day_block(day, db.get_log(day), foods, db.daily_totals(day))
    return True, ""


COMMANDS = {
    "add": cmd_add,
    "detail": cmd_detail,
    "edit": cmd_edit,
    "remove": cmd_remove,
    "rm": cmd_remove,
    "foods": cmd_foods,
    "log": cmd_log,
    "history": cmd_history,
    "help": lambda _: (True, HELP_TEXT),
    "?": lambda _: (True, HELP_TEXT),
}
