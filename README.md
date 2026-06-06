# FoodHUD (`fh`)

A minimalist, terminal-based calorie and macronutrient tracker designed to eliminate logging friction.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## The Problem

Most nutrition trackers demand immediate, meticulous entry of exact food weights and full macro breakdowns — which leads to abandonment. If logging feels like a chore, you stop doing it.

## The Solution

FoodHUD splits tracking into two decoupled phases:

1. **Frictionless Logging** — In the moment, just type `add chicken 5 oz`. If chicken isn't defined yet, it logs anyway and flags it for follow-up.
2. **Asynchronous Detailing** — Later, when convenient, run `detail chicken` and fill in the nutrition info from the label or a database.

---

## Interface

A persistent TUI HUD lives at the top of your terminal showing live daily stats, visual progress bars, and items needing attention. Commands are entered at the `fh >` prompt below.

```
================================================================================
 FOODHUD (fh)  |  Friday, June 6, 2026                               [Active]
================================================================================
 ⚠  ATTENTION REQUIRED:
   - "chicken" needs details! (Tracked in: oz)
--------------------------------------------------------------------------------
 DAILY NUTRITION  estimated from detailed items

  CALORIES   [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]   550 / 2000 kcal  ( 28%)

  FAT        [████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]    12 /   65 g  ( 18%)
  CARBS      [██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]    41 /  250 g  ( 16%)
  FIBER      [██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]     5 /   30 g  ( 16%)
  PROTEIN    [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]    30 /  150 g  ( 20%)

--------------------------------------------------------------------------------
 TODAY'S LOG:
   [✓] 1.0 item   x  chobani
   [!] 5.0 oz     x  chicken
================================================================================
 fh >
```

---

## Installation

**Requirements:** Python 3.10+

```bash
git clone https://github.com/beedz/foodhub.git
cd foodhub
pip install -r requirements.txt
```

**Run it:**
```bash
python fh.py
```

**Optional — add to PATH** so `fh` works from anywhere:

*Windows (PowerShell, run as Administrator):*
```powershell
$current = [Environment]::GetEnvironmentVariable("PATH", "User")
[Environment]::SetEnvironmentVariable("PATH", "$current;C:\path\to\foodhub", "User")
```

---

## Commands

| Command | Description |
|---|---|
| `add <food> [qty] [unit]` | Log a food item. Qty defaults to 1, unit defaults to the food's defined unit or `item`. |
| `detail <food>` | Interactive wizard — prompts for cal, fat, carbs, fiber, protein, unit with current values pre-filled. |
| `detail <food> <cal> <fat> <carbs> <fiber> <protein> [unit]` | One-liner detail entry. |
| `edit <n>` | Edit the quantity or unit of item #n in today's log. |
| `remove <n>` | Remove item #n from today's log. |
| `log [date]` | Show today's log as a table, or a specific date (`YYYY-MM-DD`). |
| `history` | Show all logged days with per-item breakdowns and daily totals. |
| `foods` | List all defined foods with their nutritional info. |
| `help` | Show command reference. |
| `quit` | Exit FoodHUD. |

---

## How Macros Are Tracked

Each food is defined with nutrition values **per 1 unit**:

```
detail chicken 55 5.5 0 0 6.9 oz
```
> 1 oz of chicken = 55 kcal, 5.5g fat, 0g carbs, 0g fiber, 6.9g protein

Then when you log `add chicken 5 oz`, FoodHUD multiplies automatically: 275 kcal, 27.5g fat, etc.

Macro order follows the **FDA nutrition label**: Calories → Fat → Carbs → Fiber → Protein.

---

## Data Storage

All data is stored locally in `~/.foodhub/data.json`. Nothing is sent anywhere.

```
~/.foodhub/
  data.json   ← food definitions + daily log
```

---

## Default Daily Goals

| Metric | Default |
|---|---|
| Calories | 2000 kcal |
| Fat | 65 g |
| Carbs | 250 g |
| Fiber | 30 g |
| Protein | 150 g |

---

## License

MIT
