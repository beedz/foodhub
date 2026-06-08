#!/usr/bin/env python3
"""FoodHUD (fh) — frictionless terminal calorie & macro tracker."""
import sys

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import StyleAndTextTuples
from rich.console import Console

import data as db
import hud
import commands as cmd

console = Console(legacy_windows=False)

EXIT_COMMANDS = {"quit", "exit", "q", ":q"}
DISPLAY_COMMANDS = {"history", "log", "foods", "help", "?", "batch"}

# Commands where the next token should be a known food name
FOOD_ARG_COMMANDS = {"add", "detail", "edit"}
# Commands where the next token should be a date
DATE_ARG_COMMANDS = {"goto", "log"}

ALL_COMMANDS = list(cmd.COMMANDS.keys()) + list(EXIT_COMMANDS)


class FoodHudCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        parts = text.lstrip().split()

        # Nothing typed yet — suggest all commands
        if not parts:
            for c in sorted(ALL_COMMANDS):
                yield Completion(c, start_position=0)
            return

        # Still typing the verb (no space yet after it)
        if len(parts) == 1 and not text.endswith(" "):
            word = parts[0].lower()
            for c in sorted(ALL_COMMANDS):
                if c.startswith(word):
                    yield Completion(c, start_position=-len(word))
            return

        verb = parts[0].lower()

        typing_second = len(parts) == 1 or (len(parts) == 2 and not text.endswith(" "))

        # Food name autocomplete for relevant commands
        if verb in FOOD_ARG_COMMANDS and typing_second:
            # typing the food name (second token)
            partial = parts[1].lower() if len(parts) == 2 else ""
            foods = db.get_foods()
            for name in sorted(foods.keys()):
                if partial in name:
                    # Show calorie info as a hint in the completion menu
                    d = foods[name]
                    meta = f"{round(d['calories'])} kcal / {d['unit']}"
                    yield Completion(
                        name,
                        start_position=-len(partial),
                        display_meta=meta,
                    )

        # Date autocomplete for goto/log
        if verb in DATE_ARG_COMMANDS and typing_second:
            partial = parts[1].lower() if len(parts) == 2 else ""
            candidates = ["today", "yesterday"] + db.get_all_days()
            for cand in candidates:
                if cand.startswith(partial):
                    meta = ""
                    if cand in ("today", "yesterday"):
                        meta = "relative"
                    yield Completion(cand, start_position=-len(partial), display_meta=meta)


COMPLETER_STYLE = Style.from_dict({
    "prompt":                "ansicyan bold",
    "completion-menu.completion":          "bg:#1e1e2e fg:#cdd6f4",
    "completion-menu.completion.current":  "bg:#313244 fg:#cba6f7 bold",
    "completion-menu.meta.completion":     "bg:#1e1e2e fg:#6c7086",
    "completion-menu.meta.completion.current": "bg:#313244 fg:#a6adc8",
})


def run() -> None:
    session: PromptSession = PromptSession(
        completer=FoodHudCompleter(),
        complete_while_typing=True,
        style=COMPLETER_STYLE,
    )

    msg: str | None = None
    msg_ok: bool = True
    skip_hud = False

    while True:
        # Pull a fresh document once per loop so a render performs one network
        # fetch (remote mode) and reflects edits from other clients.
        db.refresh()

        if not skip_hud:
            try:
                hud.render()
            except RuntimeError as e:
                console.clear()
                console.print(f"\n [bold red]⚠ Connection problem:[/bold red] {e}\n")
                console.print(" [dim]Check FOODHUB_API_URL / FOODHUB_TOKEN, or your network.[/dim]\n")

        if msg is not None:
            style = "green" if msg_ok else "red"
            console.print(f"\n [bold {style}]>[/bold {style}] {msg}\n")

        try:
            raw = session.prompt([("class:prompt", " fh > ")])
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye![/dim]")
            sys.exit(0)

        raw = raw.strip()
        if not raw:
            msg = None
            skip_hud = False
            continue

        parts = raw.split()
        verb = parts[0].lower()
        args = parts[1:]

        if verb in EXIT_COMMANDS:
            console.print("[dim]Bye![/dim]")
            sys.exit(0)

        skip_hud = verb in DISPLAY_COMMANDS

        handler = cmd.COMMANDS.get(verb)
        if handler is None:
            msg_ok = False
            msg = f'Unknown command: "{verb}". Type [bold]help[/bold] for commands.'
            skip_hud = False
        else:
            try:
                msg_ok, msg = handler(args)
            except RuntimeError as e:
                msg_ok, msg = False, str(e)
                skip_hud = False
            if not msg:
                msg = None


if __name__ == "__main__":
    run()
