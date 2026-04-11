# BARTENDER — GDD Addendum v1.1

**Difficulty Rebalance, New Cosmetics, Theme Palettes, High Score System, Font Bundling & Firebase Integration**

*April 2026*

---

This document specifies six feature additions to the Bartender (Tapper) game, intended for implementation on top of the existing Phase 4D codebase. Each section is self-contained and can be implemented as an independent phase. The phases are ordered by dependency: later phases may reference state or systems introduced in earlier ones.

The game will be deployed as a Pygbag web export hosted on GitHub Pages. Bartender uses its own dedicated Firebase Realtime Database project, separate from the HanafudaKoiKoi4x project, so there is zero risk of impacting KoiKoi's data, quota, or availability.

---

# Phase A: Difficulty Rebalance

Five changes to the level progression curve and economy: patron target count scaling, speed ramp-up rate, lives economy rework, a simplified end-of-level bonus, and contextual shop weighting.

## A.1 — Patron Target Count

The current system increases the number of patrons that must be served by 2 every level. This ramps too aggressively. The new system increases by 3, but only every other level.

### Current Behavior

```python
target_serves = LEVEL_ONE_TARGET_SERVES + ((level - 1) * LEVEL_TARGET_SERVES_STEP)
```

Where `LEVEL_TARGET_SERVES_STEP = 2`. This produces: Level 1 = 10, Level 2 = 12, Level 3 = 14, Level 4 = 16, Level 5 = 18...

### New Behavior

```python
target_serves = LEVEL_ONE_TARGET_SERVES + ((level - 1) // 2) * 3
```

This produces: Level 1 = 10, Level 2 = 10, Level 3 = 13, Level 4 = 13, Level 5 = 16, Level 6 = 16, Level 7 = 19...

The constant `LEVEL_TARGET_SERVES_STEP` (currently 2) is no longer used in its original form. It can either be removed or repurposed. A cleaner approach is to introduce two new constants:

| Constant | Value | Purpose |
|---|---|---|
| `LEVEL_TARGET_STEP_AMOUNT` | 3 | How many extra patrons per step |
| `LEVEL_TARGET_STEP_INTERVAL` | 2 | How many levels between each step |

### Files Modified

- game.py — Replace `LEVEL_TARGET_SERVES_STEP` with new constants, update `build_level_config()`.

## A.2 — Speed Ramp-Up Reduction

All three speed-scaling constants are reduced by 15% to keep the mid-game from feeling too flat (the patron count ramp is already significantly gentler from A.1, so a full 20% speed reduction on top would over-soften the curve).

| Constant | Old | New | Effect |
|---|---|---|---|
| `LEVEL_SPAWN_INTERVAL_STEP` | 0.18 | 0.153 | Spawn tightening |
| `LEVEL_MIN_WALK_SPEED_STEP` | 2.0 | 1.7 | Min patron speed |
| `LEVEL_MAX_WALK_SPEED_STEP` | 3.0 | 2.55 | Max patron speed |

### Files Modified

- game.py — Change three constant values at the top of the file. No logic changes needed.

## A.3 — Lives Economy Rework

Currently, the player gets a free +1 life every time they clear a level (in `_advance_to_next_round`). Combined with the gentler ramp from A.1 and A.2, this makes the mid-game too forgiving. Lives should be a scarce, valuable resource.

### Remove Free Life on Level Clear

Delete the line in `_advance_to_next_round()` that grants a free life:

```python
# REMOVE THIS LINE:
self.lives = min(MAX_LIVES, self.lives + 1)
```

Starting lives remain at 3. The player keeps 3 lives for the entire run unless they purchase more.

### New Shop Item: Last Call (Life Purchase)

Add a new upgrade definition that lets the player buy a life during the drink scene shop. This creates a meaningful decision: spend cash on gameplay upgrades or buy insurance.

| Field | Value |
|---|---|
| id | `"last_call"` |
| name | Last Call |
| description | Gain an extra life. |
| effect_type | `"last_call"` |
| base_cost | 5.0 |
| cost_per_level | 1.0 |
| max_stacks | 2 |
| is_cosmetic | False |
| weight | 3 |
| min_level | 1 |

When purchased, the effect is immediate: `self.lives += 1`. The `max_stacks` of 2 is the only limiter on life purchases — there is no separate total-lives cap. If the player buys two and never loses one, they'll have 5 lives; if they're buying because they're losing lives, they'll never accumulate that many. The system is self-regulating. The cost scales: first purchase is $5, second is $6. The shop weight of 3 makes it a common offer so players aren't starved of the option.

Implementation note: unlike other upgrades which modify `RunModifiers`, this one has an immediate side effect on purchase. The purchase handler in the drink scene needs a special case for `effect_type "last_call"`.

### Files Modified

- game.py — Remove free life in `_advance_to_next_round()`. Add `LAST_CALL_UPGRADE` definition. Add to `GAMEPLAY_UPGRADE_DEFINITIONS` tuple. Add purchase handler in drink scene.

## A.4 — Simplified Lives Remaining Bonus

Currently, the end-of-level bonus is 100 points per remaining life (`LIVES_REMAINING_BONUS = 100`). With lives now being scarce and purchasable, the bonus should be de-emphasized so it doesn't become a major scoring strategy. Reduce it to a modest flat bonus.

### Change

```python
LIVES_REMAINING_BONUS = 50
```

The formula stays the same (`self.lives * LIVES_REMAINING_BONUS`) — just the constant drops from 100 to 50. So at level clear with 3 lives: 3 × 50 = 150. With 1 life: 50. This keeps the bonus visible but small. The main scoring drivers remain beer serves and tips.

### Files Modified

- game.py — Change `LIVES_REMAINING_BONUS` from 100 to 50. No formula changes needed.

## A.5 — Contextual Shop Weighting

The existing shop already has weight multipliers based on level tier (early/mid/late) and affordability. This section adds a new layer: contextual weight boosts based on the player's current state, so the shop feels responsive to how the run is going.

### Design Principle

The shop should never feel rigged or manipulative — it should feel like it's paying attention. When the player is in trouble, survival options show up more often. When the player is flush with cash and doing well, bigger upgrades and cosmetics get their moment. Items are never guaranteed or forced — just nudged via weight multipliers on the existing weighted random selection.

### Contextual Multipliers

| Condition | Affected Items | Multiplier | Rationale |
|---|---|---|---|
| Player has 1 life | Last Call | ×3.0 | Survival is urgent. Make the life purchase very likely to appear. |
| Player has 2 lives | Last Call | ×1.5 | Gentle nudge. Player is under pressure but not desperate. |
| Player has 0 upgrades | All gameplay upgrades | ×1.4 | Early-run boost so new players see upgrade variety. |
| Player has no cosmetics | All cosmetics | ×1.3 | Encourage first cosmetic purchase for visual payoff. |
| Player cash > $10 | Expensive items (≥$6) | ×1.4 | When flush, show them things worth spending on. |
| Player cash < $3 | Cheap items (≤$3) | ×1.5 | Don't taunt a broke player with unaffordable options. |

### Stacking

These contextual multipliers stack multiplicatively with the existing level-tier multipliers and affordability multipliers already in the codebase. For example, if the player is at 1 life and it's an early-game shop, Last Call gets: base weight (3) × early-cheap multiplier (3.0) × contextual 1-life multiplier (3.0) = effective weight of 27. Compare that to a late-game expensive upgrade which might have effective weight of 4–8. The life purchase will dominate the pool when the player truly needs it.

### Implementation

Add a new method to the Game class:

```python
def _contextual_weight_multiplier(self, upgrade: UpgradeDefinition) -> float:
    multiplier = 1.0
    if upgrade.id == "last_call":
        if self.lives == 1:
            multiplier *= 3.0
        elif self.lives == 2:
            multiplier *= 1.5
    if not upgrade.is_cosmetic and sum(
        self.upgrade_stacks.get(u.id, 0)
        for u in GAMEPLAY_UPGRADE_DEFINITIONS
    ) == 0:
        multiplier *= 1.4
    if upgrade.is_cosmetic and not any(
        self.upgrade_stacks.get(u.id, 0) > 0
        for u in COSMETIC_UPGRADE_DEFINITIONS
    ):
        multiplier *= 1.3
    cost = ...  # resolve current cost for this upgrade
    if self.cash > 10 and cost >= 6:
        multiplier *= 1.4
    if self.cash < 3 and cost <= 3:
        multiplier *= 1.5
    return multiplier
```

Call this method during `_build_drink_scene_slots()` when calculating the effective weight for each candidate offer, alongside the existing level-tier and affordability multipliers.

### Files Modified

- game.py — Add `_contextual_weight_multiplier()` method. Update `_build_drink_scene_slots()` to call it during weight calculation.

---

# Phase B: New Cosmetics — Glasses & Cigar

Two new purchasable cosmetic items for the bartender, following the exact pattern established by the hat and bowtie cosmetics. These are permanent run-duration cosmetics (persist until game over), not single-round themes.

## B.1 — Glasses

### Upgrade Definition

| Field | Value |
|---|---|
| id | `"glasses"` |
| name | Glasses |
| description | Bartender wears glasses for the rest of the run. |
| effect_type | `"glasses"` |
| base_cost | 4 |
| max_stacks | 1 |
| is_cosmetic | True |
| weight | 1 |

### Visual Design

Small rectangular frames drawn on the bartender's face area, centered horizontally on the head. Two small rectangles (one per lens) with a thin bridge connecting them. Default color: dark brown (#3E2A1A). During gameplay, drawn in bartender.py's draw method. During the drink scene, drawn in `_draw_drink_scene_bartender()`.

### Draw Constants (game.py)

| Constant | Value | Notes |
|---|---|---|
| `DRINK_SCENE_BARTENDER_GLASSES_WIDTH` | 28 | Total width |
| `DRINK_SCENE_BARTENDER_GLASSES_HEIGHT` | 8 | Lens height |
| `DRINK_SCENE_BARTENDER_GLASSES_Y_OFFSET` | 14 | From head top |
| `DRINK_SCENE_BARTENDER_GLASSES_BRIDGE` | 4 | Bridge gap |
| `DRINK_SCENE_BARTENDER_GLASSES_COLOR` | `#3E2A1A` | Frame color |

## B.2 — Cigar

### Upgrade Definition

Same structure as glasses. id: `"cigar"`, name: "Cigar", description: "Bartender smokes a cigar for the rest of the run.", base_cost: 5, max_stacks: 1, is_cosmetic: True, weight: 1.

### Visual Design

A small brown rectangle protruding from the side of the bartender's head (the mouth area), angled slightly upward. A tiny orange-red dot at the tip represents the ember. The cigar is drawn to the right side of the head. Default body color: #6B4226. Ember color: #E85A1B.

### Draw Constants (game.py)

| Constant | Value | Notes |
|---|---|---|
| `DRINK_SCENE_BARTENDER_CIGAR_WIDTH` | 14 | Length |
| `DRINK_SCENE_BARTENDER_CIGAR_HEIGHT` | 4 | Thickness |
| `DRINK_SCENE_BARTENDER_CIGAR_Y_OFFSET` | 22 | From head top |
| `DRINK_SCENE_BARTENDER_CIGAR_X_OFFSET` | 16 | From head center |
| `DRINK_SCENE_BARTENDER_CIGAR_COLOR` | `#6B4226` | Body |
| `DRINK_SCENE_BARTENDER_CIGAR_EMBER_COLOR` | `#E85A1B` | Tip |

### State Tracking

- **`run_bartender_has_glasses: bool`** — set True on purchase, persists until game over.
- **`run_bartender_has_cigar: bool`** — set True on purchase, persists until game over.
- Both added to `_reset_game()` as False, and to the cosmetic upgrade definitions tuple.

### Files Modified

- game.py — New UpgradeDefinitions, new constants, draw logic in `_draw_drink_scene_bartender()`, state flags in `_reset_game()` and `_apply_round_cosmetic_state()`.
- bartender.py — Draw logic for glasses and cigar during gameplay (matching the hat/bowtie draw pattern).

---

# Phase C: Theme Palette System

Refactor the Green Beer Day and Wine Night cosmetic rounds so that all bartender wearables adopt the theme's color palette for the duration of that round, then revert on the next round.

## C.1 — Palette Architecture

Currently, the green/wine beer theme only changes the beer fill color (`GREEN_BEER_FILL_COLOR`, `WINE_BEER_FILL_COLOR` in glass.py). The new system extends this so the bartender's shirt, hat, bowtie, glasses, and cigar all shift to the theme's color palette during the themed round.

### Palette Data Structure

Define a dictionary of theme palettes at module level in game.py. Each palette maps cosmetic element names to their themed color override:

```python
THEME_PALETTES = {
    "green_night": {
        "shirt": Color("#2E8B2E"),
        "hat": Color("#1A6B1A"),
        "hat_brim": Color("#145214"),
        "bowtie": Color("#3DA53D"),
        "glasses": Color("#1A5C1A"),
        "cigar": Color("#3B6B3B"),
        "cigar_ember": Color("#4CAF50"),
        "apron": Color("#2D7A2D"),
    },
    "wine_night": {
        "shirt": Color("#D4839E"),
        "hat": Color("#8B2252"),
        "hat_brim": Color("#6B1A3E"),
        "bowtie": Color("#C46A8A"),
        "glasses": Color("#7A2A50"),
        "cigar": Color("#9E5070"),
        "cigar_ember": Color("#E8829E"),
        "apron": Color("#A85070"),
    },
}
```

## C.2 — Color Resolution Logic

Add a helper method to the Game class that resolves the correct color for any cosmetic element:

```python
def _resolve_cosmetic_color(self, element: str, default: Color) -> Color:
    if self.active_round_beer_theme and self.active_round_beer_theme in THEME_PALETTES:
        palette = THEME_PALETTES[self.active_round_beer_theme]
        return palette.get(element, default)
    return default
```

All draw code for cosmetic elements (hat, bowtie, glasses, cigar, shirt, apron) should call this method instead of referencing color constants directly. This applies to both the gameplay bartender (bartender.py, which will need access to the active theme) and the drink scene bartender draw code in game.py.

## C.3 — Shirt Always Themed

The shirt is always visible (it's the bartender's body). During a themed round, the shirt color always changes regardless of what cosmetics the player owns. Hat, bowtie, glasses, and cigar only change color if the player currently owns them. The apron also shifts.

## C.4 — Revert Behavior

The existing `_clear_active_round_beer_theme()` and `_activate_pending_round_beer_theme()` methods already handle the single-round lifecycle. No structural changes needed — the palette system is read-only and driven by `active_round_beer_theme`, which is already cleared at round boundaries. The underlying `run_bartender_has_*` flags are never modified by the theme system.

## C.5 — Green/Wine Night Pricing Fix

The existing `GREEN_NIGHT_UPGRADE` and `WINE_NIGHT_UPGRADE` definitions have `cost_per_level = 1`, which means the price increases by $1 every time you buy one. These should stay cheap and flat — they're fun cosmetic one-round treats, not investments. Change `cost_per_level` to 0 for both so they're always $3 regardless of how many times the player buys them across a run.

| Definition | Old | New | Effect |
|---|---|---|---|
| `GREEN_NIGHT_UPGRADE.cost_per_level` | 1 | 0 | Always $3 |
| `WINE_NIGHT_UPGRADE.cost_per_level` | 1 | 0 | Always $3 |

### Files Modified

- game.py — Add `THEME_PALETTES` dict, add `_resolve_cosmetic_color()` method, update all draw calls for bartender cosmetics in drink scene. Change `cost_per_level` to 0 for both `GREEN_NIGHT_UPGRADE` and `WINE_NIGHT_UPGRADE`.
- bartender.py — Accept optional theme palette or color overrides so gameplay bartender rendering also respects the active theme. The simplest approach: pass resolved colors into the Bartender's draw method or store them as round-level state on the Bartender instance during `_apply_round_cosmetic_state()`.

---

# Phase D: High Score System

A local high score table with 3-letter initials, profanity filtering, and a UI that fits naturally into the existing game flow.

## D.1 — High Score Data Model

### Entry Structure

| Field | Type | Description |
|---|---|---|
| initials | str (3 chars) | Player's 3-letter identifier, uppercase A–Z only |
| score | int | Final score at game over |
| level | int | Highest level reached |
| timestamp | int | Unix timestamp of submission (set server-side) |

### Leaderboard Size

The server stores the top 10 scores. The client displays the top 5 by default with an option to scroll down to see 6–10.

## D.2 — 3-Letter Initial Entry

### Input Method

Classic arcade-style entry: three character slots displayed side by side, each cycling A–Z. The player uses Up/Down to change the current letter and Left/Right to move between slots. Space or Enter confirms the entry.

### UI Layout

The initial entry screen appears after the Game Over overlay when the player's score qualifies for the top 10. It replaces the "PRESS ANY KEY TO RESTART" prompt with the initial entry interface:

- Title line: "NEW HIGH SCORE!" in the overlay font, centered.
- Score display: the player's final score and level, centered below the title.
- Three letter slots: large characters with a blinking underscore beneath the active slot (see S.8). Each slot shows the currently selected letter.
- Prompt: "ENTER YOUR INITIALS" below the slots.
- Confirm prompt: "PRESS ENTER TO SUBMIT" at the bottom.

### State

New fields on the Game class:

- **`high_score_entry_active: bool`** — True when the initial entry screen is showing.
- **`high_score_initials: list[int]`** — Three integers (0–25) representing the selected letter index per slot.
- **`high_score_cursor: int`** — Which slot (0, 1, or 2) is currently active.

## D.3 — Profanity Filter (Client-Side UX Mirror)

The authoritative profanity filter lives server-side in the Firebase security rules (see Phase E.2). However, a matching client-side blocklist is kept in game.py so the player gets instant visual feedback — the entry flashes red and does not attempt submission — rather than waiting for a server round-trip rejection.

### Client-Side Blocklist

Store as a frozenset of uppercase strings in game.py. This list must stay in sync with the server-side regex pattern in the Firebase validation rules:

```python
BLOCKED_INITIALS = frozenset({
    "ASS", "FUK", "FUC", "FCK", "SHT", "SHI", "DIK", "DIQ",
    "DIC", "COK", "COC", "CUM", "FAG", "FAT", "GAY", "GOD",
    "JEW", "KKK", "NIG", "NGA", "NGR", "PIS", "POO", "SEX",
    "TIT", "TTS", "WTF", "STF", "SUK", "SUC", "VAG", "WOP",
    "KYS", "RAP", "FKU", "CNT", "CUN", "HOR", "HO3",
    "ANU", "ANL", "BUT", "BUM", "DAM", "DMN", "HEL",
    "JIZ", "KIK", "PEN", "PHK", "SCK", "SLT", "SMD",
})
```

This is a UX convenience only. Even if someone bypasses the client, the server will reject the write. The client check prevents a wasted round-trip and gives a nicer error. The list can be expanded over time but must be kept in sync with the server-side regex.

## D.4 — High Score Display UI

The high score table is shown on the title screen / game-over screen. It must not clutter the existing UI.

### Layout Strategy

The high score table appears in the lower portion of the screen, below the game-over text. It uses a compact monospaced format:

```
  # | INI | LVL | SCORE
  1   AAA    7   2,450
  2   BCD    5   1,800
  3   EFG    4   1,200
  4   HIJ    3     950
  5   KLM    2     600
```

### Scroll Behavior

By default, only the top 5 are visible. A small downward-pointing triangle indicator appears below row 5 if more entries exist. The player presses Down to reveal rows 6–10. When scrolled down, an upward-pointing triangle appears above row 6. The scroll state is a simple integer offset (0 = showing 1–5, 1 = showing 6–10). Only two positions, no smooth scrolling needed.

### Visual Constraints

- Font: use the existing detail_font (monospaced, 12pt bold — will be the bundled TTF after Phase F).
- Color: `OVERLAY_TEXT_COLOR` (#F5F0E8) for text, slightly dimmer for the rank numbers.
- The table header row (# | INI | LVL | SCORE) uses a slightly different color or underline to distinguish it.
- The player's own score, if it appears on the board, is highlighted with `DRINK_SCENE_CONTINUE_BONUS_COLOR` (#E7C05A).
- Total vertical space budget: approximately 80–90 pixels for 5 rows plus header. This fits comfortably in the lower third of the 300px logical height.

### Integration with Game Over Screen

The game-over overlay currently shows "GAME OVER" and "PRESS ANY KEY TO RESTART". The new flow:

1. Game Over triggers. The overlay appears with "GAME OVER" title.
2. If the score qualifies for top 10: show the initial entry screen instead of "PRESS ANY KEY". After entry, submit to server, refresh the leaderboard, then show the table with the new entry highlighted.
3. If the score does not qualify: show the leaderboard table directly below the game-over text, along with "PRESS ANY KEY TO RESTART".
4. After viewing the leaderboard (with or without entry), any key press restarts the game.

### New FlowState

Add `HIGH_SCORE_ENTRY` to the FlowState enum. This state is entered from GAME_OVER when the score qualifies. It transitions back to GAME_OVER (with leaderboard visible) after submission.

### Files Modified

- game.py — New FlowState, initial entry logic, draw methods, profanity filter, leaderboard display, scroll state.
- hud.py — No changes; the leaderboard is drawn in the game-over overlay, not the HUD.

---

# Phase E: Firebase Integration

Connect the high score system to a dedicated Firebase Realtime Database project. This is a separate project from the KoiKoi game, giving Bartender its own quota, rules, and data — completely isolating the two games from each other.

## E.1 — Firebase Project Setup

### ⚠️ MANUAL STEP — You (Falk) Must Do This First

Before any code is written for this phase, create the Firebase project:

1. Go to console.firebase.google.com and click Add Project.
2. Name it something like "bartender-leaderboard" (the exact name doesn't matter).
3. You can skip Google Analytics — it's not needed.
4. Once created, go to Build → Realtime Database → Create Database.
5. Choose any region (us-central1 is fine). Start in locked mode — you'll set the real rules in step E.2.
6. Copy the database URL from the top of the data viewer (e.g. `https://bartender-leaderboard-default-rtdb.firebaseio.com`). You'll paste this into network.py later.

### Database Structure

The database is simple — a single top-level key with leaderboard entries:

```
/ (database root)
└── highscores/
    ├── -Nxyz123: { initials: "AAA", score: 2450, level: 7, timestamp: 1712700000 }
    ├── -Nxyz124: { initials: "BCD", score: 1800, level: 5, timestamp: 1712700100 }
    └── ...
```

Entries use Firebase push IDs as keys. The database is queried with `orderByChild("score")` and `limitToLast(10)` to retrieve only the top 10.

## E.2 — Firebase Security Rules (Server-Side Profanity Filter)

These are the complete rules for the Bartender project. Since this is a dedicated project, these are the only rules needed. The write rule uses `!data.exists()` so entries can only be created, never overwritten or deleted by clients. This prevents spam attacks from wiping the leaderboard.

```json
{
  "rules": {
    "highscores": {
      ".read": true,
      ".indexOn": ["score"],
      "$entry": {
        ".write": "!data.exists()",
        ".validate": "newData.hasChildren(['initials','score','level','timestamp'])
          && newData.child('initials').isString()
          && newData.child('initials').val().length == 3
          && newData.child('initials').val().matches(/^[A-Z]{3}$/)
          && !newData.child('initials').val().matches(/^(ASS|FUK|FUC|FCK|SHT|SHI|DIK|DIQ|DIC|COK|COC|CUM|FAG|FAT|GAY|GOD|JEW|KKK|NIG|NGA|NGR|PIS|POO|SEX|TIT|TTS|WTF|STF|SUK|SUC|VAG|WOP|KYS|RAP|FKU|CNT|CUN|HOR|HO3|ANU|ANL|BUT|BUM|DAM|DMN|HEL|JIZ|KIK|PEN|PHK|SCK|SLT|SMD)$/)
          && newData.child('score').isNumber()
          && newData.child('score').val() >= 0
          && newData.child('score').val() <= 99999
          && newData.child('level').isNumber()
          && newData.child('level').val() >= 1
          && newData.child('level').val() <= 999
          && newData.child('timestamp').isNumber()"
      }
    }
  }
}
```

Key details: The `.indexOn` for "score" is required for the `orderByChild` query. The `!data.exists()` write rule means each push ID can only be written once — no overwrites, no deletes from clients. Score is capped at 99,999 and level at 999 as basic anti-cheat sanity checks. If you ever need to clean up old entries, do it manually in the Firebase Console.

### ⚠️ MANUAL STEP — You (Falk) Must Do This

The coding agent cannot deploy Firebase rules. You need to:

1. Open the Firebase Console for your new Bartender project (created in E.1).
2. Go to Realtime Database → Rules tab.
3. Replace the default locked-mode rules with the complete ruleset shown above.
4. Click Publish.
5. Test: In the data viewer, try manually adding a test entry under /highscores/ with valid initials (e.g. `{"initials":"AAA","score":100,"level":1,"timestamp":1234567890}`). Then try one with blocked initials (e.g. "ASS") to confirm the rule rejects it.

## E.3 — Client Implementation (Pygbag)

Since Bartender runs as a Pygbag web export, it executes in the browser via Pyodide/Emscripten. HTTP requests to Firebase REST API are available through the JavaScript interop layer.

### Firebase REST API Endpoints

| Action | Method | URL Pattern |
|---|---|---|
| Read top 10 | GET | `/highscores.json?orderBy="score"&limitToLast=10` |
| Submit score | POST | `/highscores.json` |

### Network Module

Create a new file, network.py, that encapsulates all Firebase communication. This module provides two async functions:

- **`fetch_leaderboard() -> list[dict]`** — Returns the top 10 entries sorted by score descending. Called on game startup and after each score submission.
- **`submit_score(initials: str, score: int, level: int) -> bool`** — POSTs a new entry. Returns True on success. The timestamp is set using server time (`{".sv": "timestamp"}` in the POST body).

In Pygbag, HTTP requests use `platform.window.fetch()` (JavaScript interop). The module should handle network errors gracefully: if Firebase is unreachable, the game continues normally with an empty or stale leaderboard and the score submission silently fails. The game must never block or crash due to network issues.

### Firebase Config

The Firebase project URL is from the dedicated Bartender project created in E.1. It should be stored as a single constant at the top of network.py:

```python
FIREBASE_URL = "https://<your-bartender-project-id>.firebaseio.com"
```

### ⚠️ MANUAL STEP — You (Falk) Must Do This

After the coding agent creates network.py with the placeholder URL:

1. Open the Bartender Firebase project's Console (not KoiKoi's).
2. Go to Realtime Database. Copy the database URL from the top of the data viewer.
3. Open network.py and replace the placeholder in `FIREBASE_URL` with your actual URL.

The Bartender game only uses the Firebase REST API (not the Firebase JS SDK), so no additional SDK initialization or API key config is needed beyond this URL.

## E.4 — Leaderboard Pruning

Since the security rules use `!data.exists()` (create-only, no deletes), client-side pruning is not possible. This is an intentional tradeoff for security. The database will grow by one entry per qualifying game-over, but this is extremely slow growth — even with heavy play, you'd accumulate maybe a few hundred entries over months.

The client still only queries `limitToLast(10)`, so extra entries don't affect performance or display. If the database ever needs cleaning, do it manually in the Firebase Console by deleting old low-scoring entries. This should be a very rare maintenance task.

### Files Created

- network.py — New file. All Firebase REST API communication.

### Files Modified

- game.py — Import network module. Call `fetch_leaderboard()` on startup and after submission. Call `submit_score()` from the high score entry flow. Store cached leaderboard data on the Game instance.
- main.py — May need async initialization for the network module's first leaderboard fetch.

---

# Implementation Order & Dependencies

| Phase | Name | Depends On | Complexity | Manual Steps? |
|---|---|---|---|---|
| A | Difficulty Rebalance | None | Medium | No |
| B + C | Cosmetics + Theme Palettes | None (do together) | Medium | No |
| F | Font Bundling | None | Low | No |
| D | High Score System | F (fonts stable) | Medium | No |
| E | Firebase Integration | D | High | YES |

Recommended sequence: A first (low-risk, game.py only), then B+C together (they share the cosmetic/render plumbing), then F (font bundling — must be stable before the text-heavy leaderboard work), then D, then E last since it depends on the leaderboard flow existing. A and B+C can be done in parallel if desired.

## Manual Steps Summary (Falk's Checklist)

These are the steps the coding agent cannot do for you. They are marked with ⚠️ in the relevant phase sections above.

| Phase | Step | What to Do |
|---|---|---|
| E.1 | Create Firebase Project | Create a new project in the Firebase Console (separate from KoiKoi). Set up a Realtime Database. Copy the database URL. |
| E.2 | Deploy Security Rules | In the new project, go to Realtime Database → Rules. Paste the complete ruleset from E.2. Publish. |
| E.2 | Test Rule Validation | In the data viewer, add a test entry with valid initials (should succeed) and blocked initials (should fail). |
| E.3 | Paste Firebase URL | Copy the database URL from your Bartender project. Paste into FIREBASE_URL in network.py. |

---

# Spec Tightening Notes

These are implementation details that cut across multiple phases. They exist to prevent ambiguity and common pitfalls when the coding agent works through the phases.

## S.1 — High Score Qualification Logic

The game needs to determine whether a score qualifies for the leaderboard before showing the initial entry screen. The logic:

- **If the cached leaderboard has fewer than 10 entries:** any score qualifies.
- **If the cached leaderboard has 10 entries:** the player's score must be strictly greater than the 10th-place score.
- **If the cached leaderboard is empty or stale (fetch failed):** any score qualifies. The submission may fail server-side, which is fine — better to let the player enter initials optimistically than deny them because of a network hiccup.

Store the cached leaderboard as a list on the Game instance (e.g. `self.cached_leaderboard`). Initialize it as an empty list. The qualifying check is a simple comparison against the last entry in the sorted list.

## S.2 — Leaderboard Fetch Timing & Error Handling

The leaderboard is fetched at three points:

- **On game startup:** fire-and-forget. If it fails, the game starts with an empty cached leaderboard. No retry, no error message.
- **After a successful score submission:** fetch again to refresh the board with the new entry. If this fetch fails, display the stale cached data with the new entry optimistically inserted client-side.
- **Never during gameplay:** no fetches happen while a round is in progress.

There should be no retry logic. Network calls are best-effort. The game must never stall, show a loading spinner, or wait for a response before proceeding. If the leaderboard is unavailable, the game-over screen simply omits the table (see S.10).

## S.3 — Pygbag Async Pattern

The Bartender game loop is synchronous (pygame's standard update/draw/tick cycle). Network calls are async. This is a common Pygbag pitfall. The pattern to use:

All network calls should be fire-and-forget with a callback that updates cached state. The game loop never awaits a network response. Instead:

- **Start the request:** call the async function, which returns immediately.
- **The async function runs in the background:** using `platform.window.fetch()` via JavaScript interop.
- **On completion:** the callback updates `self.cached_leaderboard` (or sets a flag like `self.submission_complete = True`).
- **The game loop polls the flag:** on the next `update()` tick, it notices the new data and updates the display.

In Pygbag, the standard approach is `asyncio.ensure_future()` to kick off the coroutine without blocking. The network.py module should expose simple functions that handle the async plumbing internally and update state via a reference to the Game instance or a shared state object.

## S.4 — Server Rejection Feedback

If the client-side profanity filter is somehow bypassed and the server rejects the write (returns a non-200 status), the game should:

- **Not crash or hang.** The submission just silently fails.
- **Show the game-over screen normally** with "PRESS ANY KEY TO RESTART". The player's score simply doesn't appear on the leaderboard.
- **Log the error to console** for debugging, but no user-facing error message is needed.

## S.5 — Cosmetic Draw Order

With four wearable cosmetics, the z-ordering during draw matters. Both in gameplay (bartender.py) and the drink scene (game.py), draw in this order (back to front):

1. Body/shirt (always drawn)
2. Apron (always drawn)
3. Bowtie (if owned)
4. Head
5. Glasses (if owned) — drawn on top of face
6. Cigar (if owned) — drawn on top of face, protruding right
7. Hat (if owned) — drawn on top of head, overlapping hair/top of head

This ensures the hat sits on top of everything, the cigar and glasses layer correctly over the face, and the bowtie sits at the collar below the head.

## S.6 — Theme Color Propagation to bartender.py

The drink scene bartender is drawn entirely within game.py, so theme colors are easy to resolve there. But the gameplay bartender is drawn by bartender.py, which doesn't have access to the Game's theme state.

The cleanest approach: during `_apply_round_cosmetic_state()`, resolve all themed colors using `_resolve_cosmetic_color()` and set them as attributes directly on the Bartender instance:

```python
self.bartender.shirt_color = self._resolve_cosmetic_color("shirt", DEFAULT_SHIRT_COLOR)
self.bartender.hat_color = self._resolve_cosmetic_color("hat", DEFAULT_HAT_COLOR)
# ... etc for each cosmetic element
```

Then bartender.py's draw method reads `self.shirt_color`, `self.hat_color`, etc. instead of module-level constants. These attributes get set fresh every round via `_apply_round_cosmetic_state()`, so they automatically revert when a theme ends. This avoids passing the Game instance or theme state into bartender.py and keeps the two modules loosely coupled.

## S.7 — Game-Over Input Conflicts

On the game-over screen, "PRESS ANY KEY TO RESTART" must not conflict with the leaderboard scroll. When the leaderboard is visible, Up and Down are consumed by the scroll and do not trigger a restart. Only non-directional keys (any key besides Up/Down) should restart the game. This prevents the player from accidentally restarting when they're trying to scroll to entries 6–10.

## S.8 — Initial Entry Cursor Visual

The active letter slot in the high score entry screen uses a blinking underscore beneath the active letter, toggling visibility every 0.4 seconds (on for 0.4s, off for 0.4s). Inactive slots show no underscore. This is a concrete spec — the coding agent should not make a design decision here.

## S.9 — Shop Slot Count Confirmation

The drink scene shop continues to show exactly 3 slots. Despite the upgrade pool growing to 13 items (7 gameplay including Last Call + 6 cosmetics including glasses/cigar), the slot count stays at 3. The contextual weighting system (A.5) handles surfacing the right items. Do not change the slot count.

## S.10 — Leaderboard Empty State

If the cached leaderboard is empty (no entries, or network fetch failed), the game-over screen should skip the leaderboard table entirely and just show "PRESS ANY KEY TO RESTART" below the game-over title. No "LEADERBOARD UNAVAILABLE" text, no empty table frame — just omit it cleanly. The scroll indicators also do not appear when there's no data.

## S.11 — Leaderboard Scroll State Reset

When a new game starts (`_reset_game()`), the leaderboard scroll position resets to 0 (showing top 5). If the player scrolled down to 6–10 on the previous game-over screen, that scroll offset must not carry over to the next game-over.

## S.12 — Contextual Weighting on Maxed Items

Contextual weight multipliers (A.5) must only apply to items that pass the `can_offer` check. If Last Call is already at `max_stacks`, its weight boost for being at 1 life is irrelevant — the item should be filtered out of the candidate pool before weights are calculated, not after. The existing `_build_drink_scene_slots()` method likely already filters by `can_offer`, but this ordering must be preserved: filter first, then apply weights to survivors.

## S.13 — Font Bundling (Phase F)

The codebase uses `pygame.font.SysFont("couriernew", ...)` throughout. In a Pygbag browser build, system fonts are not guaranteed to be available. This is promoted to its own implementation step (Phase F) between C and D because the leaderboard UI in Phase D is heavily text-dependent and should be built on stable font rendering.

The coding agent should bundle a monospaced TTF font file (e.g. Courier Prime or similar open-license mono font) and replace all `SysFont` calls with `pygame.font.Font("path/to/font.ttf", size)`. This affects game.py (`overlay_font`, `detail_font`, `drink_scene_title_font`, `drink_scene_detail_font`) and hud.py. If the font file is missing at runtime, fall back to `pygame.font.Font(None, size)` (pygame's built-in default) rather than crashing.

---

# Test Plan

Manual testing checklist for each phase. Run through the relevant section after the coding agent delivers each phase. Each item is a pass/fail check. If a check fails, file it as a bug for the agent to fix before moving to the next phase.

## Phase A Tests

### A.1 — Patron Target Count
- [ ] Start a new game. Level 1 requires 10 patrons served. Confirm via HUD.
- [ ] Clear level 1. Level 2 also requires 10 patrons. Confirm the count did NOT increase.
- [ ] Clear level 2. Level 3 requires 13 patrons. Confirm the +3 step happened.
- [ ] Clear level 3. Level 4 also requires 13. Confirm no increase on the odd-to-even transition.

### A.2 — Speed Ramp-Up
- [ ] Play levels 1 through 4. Patrons should feel noticeably but not dramatically faster each pair of levels.
- [ ] Compare subjectively to the old build if available. The ramp should feel about 15% gentler.

### A.3 — Lives Economy
- [ ] Start a new game. Confirm 3 lives shown in HUD.
- [ ] Clear level 1. Confirm lives did NOT increase to 4 (free life removed).
- [ ] Lose a life. Confirm lives drops to 2. Clear the level. Confirm lives stays at 2.
- [ ] In the drink scene shop, confirm Last Call appears as a purchasable option (may need multiple runs to see it due to random selection).
- [ ] Purchase Last Call. Confirm lives increases by 1 immediately.
- [ ] Purchase Last Call a second time (if offered). Confirm it works.
- [ ] Confirm Last Call is NOT offered a third time (max_stacks = 2).

### A.4 — Simplified Bonus
- [ ] Clear level 1 with 3 lives. Confirm lives bonus in the drink scene summary is 150 (3 × 50).
- [ ] Clear any level with 1 life. Confirm lives bonus is 50.

### A.5 — Contextual Shop Weighting
- [ ] Play until you have 1 life. Clear a level. Confirm Last Call appears in the shop (run this 5+ times — it should appear in the vast majority of shops at 1 life).
- [ ] Play with full lives and high cash (>$10). Confirm the shop tends to show more expensive items.
- [ ] Play with very low cash (<$3). Confirm the shop tends to show cheaper items.

## Phase B Tests

### B.1 — Glasses
- [ ] Confirm Glasses appears as a shop offer (may take multiple runs).
- [ ] Purchase Glasses. Confirm the bartender visually wears glasses during gameplay.
- [ ] Confirm glasses persist across level clears (still visible in next round).
- [ ] Confirm glasses disappear on game over and new game start.
- [ ] Confirm Glasses is NOT offered again after purchase (max_stacks = 1).
- [ ] Confirm glasses appear on the drink scene bartender as well.

### B.2 — Cigar
- [ ] Same test sequence as Glasses but for the Cigar cosmetic.
- [ ] Purchase both Glasses and Cigar in the same run. Confirm both render correctly without visual overlap/clipping.

## Phase C Tests

### C.1 — Green Beer Day
- [ ] Purchase Green Night in the drink scene. Confirm the next round has green beer fill color.
- [ ] Confirm the bartender's shirt is green during the green round.
- [ ] If you own a hat: confirm the hat is green. If you don't own a hat: confirm no green hat appears (it shouldn't grant items you don't own).
- [ ] Same check for bowtie, glasses, and cigar — only change color if owned.
- [ ] Confirm the apron is also green.
- [ ] Clear the green round. Confirm the NEXT round reverts all colors to their defaults.
- [ ] Confirm the underlying cosmetic ownership is unaffected (you still have your hat/bowtie/etc. in normal colors).

### C.2 — Wine Night
- [ ] Same test sequence as Green Beer Day but with pink/wine palette.

### C.3 — Edge Cases
- [ ] Purchase Green Night, then lose a life during the green round (triggering fail/reset). Confirm the next round is NOT green (theme consumed).
- [ ] Purchase Green Night and Wine Night in the same shop (if both offered). Confirm only the last purchased one takes effect on the next round.

### C.5 — Flat Pricing
- [ ] Purchase Green Night. Note the cost ($3).
- [ ] In a later shop, confirm Green Night is offered again at $3 (not $4).
- [ ] Purchase it a third time. Confirm still $3.
- [ ] Same check for Wine Night.

## Phase F Tests (Font Bundling)

- [ ] Run the game locally (pygame). Confirm all text renders with the bundled font, not a system fallback.
- [ ] Delete or rename the bundled TTF file. Launch the game. Confirm it falls back to pygame's default font and does NOT crash.
- [ ] Run the Pygbag build in a browser. Confirm all text (HUD, overlays, drink scene labels) renders correctly as monospaced.
- [ ] Check the browser console for any font-related warnings or errors.

## Phase D Tests

### D.1 — Qualifying Score Check
- [ ] On first-ever play (empty leaderboard): die with any score. Confirm the initial entry screen appears.
- [ ] After 10 entries exist: die with a score lower than 10th place. Confirm the entry screen does NOT appear and the leaderboard is shown directly.
- [ ] After 10 entries exist: die with a score higher than 10th place. Confirm the entry screen appears.

### D.2 — Initial Entry
- [ ] Confirm three letter slots appear, defaulting to AAA.
- [ ] Press Up/Down. Confirm the active slot cycles A→B→...→Z→A.
- [ ] Press Left/Right. Confirm the cursor moves between slots.
- [ ] Enter valid initials (e.g. "JKL") and press Enter. Confirm submission.

### D.3 — Profanity Filter
- [ ] Enter "ASS" and press Enter. Confirm the entry flashes red and does NOT submit.
- [ ] Enter "AAA" and press Enter. Confirm it submits normally.
- [ ] Test at least 3 other blocked words from the list.

### D.4 — Leaderboard Display
- [ ] After submitting a score, confirm the leaderboard shows on the game-over screen.
- [ ] Confirm the top 5 are visible by default.
- [ ] Press Down. Confirm rows 6–10 become visible.
- [ ] Press Up. Confirm it scrolls back to rows 1–5.
- [ ] Confirm the player's own entry is highlighted in gold (#E7C05A).
- [ ] Confirm each entry shows rank, initials, level, and score.

## Phase E Tests

### E.1 — Firebase Project
- [ ] Confirm the Bartender Firebase project exists and has a Realtime Database.
- [ ] Confirm the KoiKoi Firebase project is completely untouched.

### E.2 — Security Rules
- [ ] In the Firebase Console data viewer, manually add a valid entry. Confirm it succeeds.
- [ ] Manually add an entry with blocked initials (e.g. "ASS"). Confirm the write is rejected.
- [ ] Manually add an entry with score > 99999. Confirm rejected.
- [ ] Manually add an entry with non-uppercase initials (e.g. "abc"). Confirm rejected.
- [ ] Try to overwrite an existing entry. Confirm rejected (!data.exists() rule).
- [ ] Try to delete an existing entry. Confirm rejected.

### E.3 — Client Integration
- [ ] Launch the game (Pygbag build). Confirm the leaderboard loads from Firebase on startup (check browser console for network request).
- [ ] Submit a high score. Confirm it appears in the Firebase Console data viewer.
- [ ] Submit a high score. Confirm the leaderboard refreshes and shows the new entry.
- [ ] Disconnect from the internet. Launch the game. Confirm it starts normally with an empty leaderboard (no crash, no hang).
- [ ] Disconnect from the internet. Die with a qualifying score. Enter initials and submit. Confirm the game handles the failure gracefully (no crash, proceeds to game-over screen).
- [ ] Reconnect. Play again. Confirm the leaderboard fetches successfully on the next startup.

### E.4 — Cross-Game Isolation
- [ ] While Bartender is running and submitting scores, open the KoiKoi game in another tab.
- [ ] Confirm KoiKoi functions normally (lobbies, multiplayer, all features).
- [ ] Confirm the KoiKoi Firebase project has no bartender data in it.

## Cross-Cutting Tests (Spec Tightening)

### S.7 — Input Conflicts
- [ ] On game-over with leaderboard visible, press Down. Confirm the leaderboard scrolls and the game does NOT restart.
- [ ] Press Up to scroll back. Confirm no restart.
- [ ] Press Space or Enter. Confirm the game restarts.

### S.8 — Cursor Blink
- [ ] On the initial entry screen, confirm the active slot has a blinking underscore.
- [ ] Confirm inactive slots do not have an underscore.
- [ ] Move the cursor to a different slot. Confirm the underscore follows.

### S.9 — Slot Count
- [ ] Across multiple level clears, confirm the drink scene always shows exactly 3 slots.

### S.10 — Empty Leaderboard
- [ ] Clear all entries from Firebase (manually in console). Die in-game. Confirm the game-over screen shows no leaderboard table — just the game-over text and restart prompt.
- [ ] Disconnect from internet before starting the game. Die. Confirm the same clean game-over screen with no table.

### S.11 — Scroll Reset
- [ ] Die with a qualifying score. Submit initials. Scroll down to see entries 6–10.
- [ ] Press a key to restart. Play and die again. Confirm the leaderboard starts at entries 1–5, not 6–10.

### S.13 — Font Rendering
- [ ] Run the Pygbag build in a browser. Confirm all text renders correctly with a monospaced font.
- [ ] Confirm no font fallback warnings in the browser console.

---

*End of Document*
