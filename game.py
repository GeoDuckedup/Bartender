from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from random import Random

import pygame

from bartender import BARTENDER_CATCH_RECT_PADDING, BARTENDER_WALK_SPEED, Bartender
from glass import (
    FLYING_GLASS_SPEED,
    GREEN_BEER_FILL_COLOR,
    TAP_FILL_DURATION,
    ReturningGlass,
    WINE_BEER_FILL_COLOR,
    draw_glass_with_fill,
)
from hud import HUDRenderer
from patron import PATRON_ARCHETYPES, Patron, build_walk_speed_rng
from renderer import BAR_COUNT, GLASS_OUTLINE_COLOR, SceneRenderer
from tip import Tip


# Level pacing tuning:
# Early levels stay forgiving, then difficulty ramps through target count,
# spawn cadence, and patron speed.
LEVEL_ONE_TARGET_SERVES = 10
LEVEL_TARGET_STEP_AMOUNT = 3
LEVEL_TARGET_STEP_INTERVAL = 2
LEVEL_ONE_SPAWN_INTERVAL = 3.0
LEVEL_SPAWN_INTERVAL_STEP = 0.17
MIN_SPAWN_INTERVAL = 0.75
LEVEL_ONE_MIN_WALK_SPEED = 16.0
LEVEL_MIN_WALK_SPEED_STEP = 1.9
LEVEL_ONE_MAX_WALK_SPEED = 24.0
LEVEL_MAX_WALK_SPEED_STEP = 2.8
LEVEL_ONE_SHOVE_WEIGHTS = (0.60, 0.25, 0.15)
LEVEL_TWO_SHOVE_WEIGHTS = (0.55, 0.30, 0.15)
LEVEL_THREE_PLUS_SHOVE_WEIGHTS = (0.50, 0.35, 0.15)

# Run / scoring tuning:
# These values define the overall run economy, coin rewards, and level-clear bonus flow.
MAX_PATRONS_PER_LANE = 3
STARTING_LIVES = 3
MAX_LIVES = 99
STARTING_CASH = 0.0
BEER_SERVED_SCORE = 10
TIP_SCORE = 25
BEER_SERVED_CASH = 0.5
TIP_CASH = 1.0
TIP_SPAWN_RATE_MULTIPLIER = 1.2
LIVES_REMAINING_BONUS = 50

# Spawn / patron variety tuning:
# The first spawn delay makes rounds feel responsive without affecting
# the ongoing steady-state spawn interval for the level.
FIRST_PATRON_DELAY = 0.35
MIN_DRINK_DURATION = 0.95
MAX_DRINK_DURATION = 1.45
TIP_RNG_SEED = 1984

# Fail feedback tuning:
# These only affect the readability of a lost round, not the rules.
FAIL_FEEDBACK_DURATION = 0.6
FAIL_SHAKE_AMPLITUDE = 4
FAIL_SHAKE_PATTERN = (
    (0, 0),
    (FAIL_SHAKE_AMPLITUDE, -2),
    (-FAIL_SHAKE_AMPLITUDE, 2),
    (2, -1),
    (-2, 1),
)
FAIL_SHAKE_FPS = 30

# Overlay / scene text tuning:
# Shared text colors and game-over positions live here. The old level-clear
# overlay positions were removed once the dedicated reward scene replaced it.
OVERLAY_TEXT_COLOR = pygame.Color("#F5F0E8")
GAME_OVER_TITLE_Y = 138
GAME_OVER_PROMPT_Y = 160
DRINK_SCENE_PURCHASED_GLOW_COLOR = pygame.Color("#E7C05A")
DRINK_SCENE_PURCHASED_LABEL = "BOUGHT"

# Level-clear drink scene layout:
# This dedicated reward scene replaces the old gameplay overlay and gives us
# a larger stage to build the bartender drinking sequence on top of.
DRINK_SCENE_BACKGROUND_COLOR = pygame.Color("#1C0F09")
DRINK_SCENE_SIGN_FRAME_COLOR = pygame.Color("#8E4021")
DRINK_SCENE_SIGN_GLOW_COLOR = pygame.Color("#D66B2C")
DRINK_SCENE_SIGN_TEXT_COLOR = pygame.Color("#FFE9BF")
DRINK_SCENE_BAR_TOP_COLOR = pygame.Color("#D07C2F")
DRINK_SCENE_BAR_FRONT_COLOR = pygame.Color("#9A551E")
DRINK_SCENE_BAR_TRIM_COLOR = pygame.Color("#5A2E14")
DRINK_SCENE_COUNTER_COLOR = pygame.Color("#3E1E11")
DRINK_SCENE_BARTENDER_SHIRT_COLOR = pygame.Color("#F2EFE6")
DRINK_SCENE_BARTENDER_SKIN_COLOR = pygame.Color("#F6D6A2")
DRINK_SCENE_BARTENDER_APRON_COLOR = pygame.Color("#9A7812")
DRINK_SCENE_SELECTED_OUTLINE_COLOR = GLASS_OUTLINE_COLOR
DRINK_SCENE_UNAFFORDABLE_COLOR = pygame.Color("#D36A61")
DRINK_SCENE_CONTINUE_BONUS_COLOR = pygame.Color("#E7C05A")
DRINK_SCENE_SIGN_Y = 68
DRINK_SCENE_SIGN_WIDTH = 300
DRINK_SCENE_SIGN_HEIGHT = 52
DRINK_SCENE_SIGN_GLOW_INFLATE = 14
DRINK_SCENE_SIGN_GLOW_RADIUS = 12
DRINK_SCENE_SIGN_BACKGROUND_INSET = 6
DRINK_SCENE_SIGN_FRAME_RADIUS = 10
DRINK_SCENE_SIGN_INNER_FRAME_INSET = 8
DRINK_SCENE_SIGN_INNER_FRAME_WIDTH = 3
DRINK_SCENE_SIGN_INNER_FRAME_RADIUS = 8
DRINK_SCENE_CASH_X_OFFSET = 6
DRINK_SCENE_CASH_Y_OFFSET = 12
DRINK_SCENE_BAR_WIDTH = 344
DRINK_SCENE_BAR_HEIGHT = 68
DRINK_SCENE_BAR_Y = 208
DRINK_SCENE_BAR_TOP_HEIGHT = 16
DRINK_SCENE_BAR_TRIM_HEIGHT = 10
DRINK_SCENE_BAR_COUNTER_HEIGHT = 12
DRINK_SCENE_BAR_DIVIDER_LINE_WIDTH = 3
DRINK_SCENE_SLOT_Y = 176
DRINK_SCENE_SLOT_SPACING = 98
DRINK_SCENE_SLOT_WIDTH = 32
DRINK_SCENE_SLOT_HEIGHT = 48
DRINK_SCENE_LABEL_Y = 246
DRINK_SCENE_BONUS_Y = 264
DRINK_SCENE_COST_Y = 272
DRINK_SCENE_STATUS_Y = 290
DRINK_SCENE_SLOT_PURCHASED_GLOW_INFLATE = 10
DRINK_SCENE_SLOT_PURCHASED_GLOW_WIDTH = 3
DRINK_SCENE_SLOT_PURCHASED_GLOW_RADIUS = 8
DRINK_SCENE_SLOT_SELECTED_HIGHLIGHT_INFLATE = 8
DRINK_SCENE_SLOT_SELECTED_HIGHLIGHT_WIDTH = 2
DRINK_SCENE_SLOT_SELECTED_HIGHLIGHT_RADIUS = 6
DRINK_SCENE_BARTENDER_BODY_WIDTH = 54
DRINK_SCENE_BARTENDER_BODY_HEIGHT = 92
DRINK_SCENE_BARTENDER_HEAD_SIZE = 34
DRINK_SCENE_BARTENDER_SLOT_CENTER_OFFSET = 22
DRINK_SCENE_BARTENDER_BODY_BOTTOM_OFFSET = 26
DRINK_SCENE_BARTENDER_APRON_WIDTH = 22
DRINK_SCENE_BARTENDER_APRON_Y = 24
DRINK_SCENE_BARTENDER_APRON_BOTTOM_PADDING = 8
DRINK_SCENE_BARTENDER_ARM_WIDTH = 14
DRINK_SCENE_BARTENDER_ARM_HEIGHT = 44
DRINK_SCENE_BARTENDER_LEFT_ARM_X_OFFSET = -10
DRINK_SCENE_BARTENDER_LEFT_ARM_Y_OFFSET = 22
DRINK_SCENE_BARTENDER_RIGHT_ARM_X_OFFSET = -4
DRINK_SCENE_BARTENDER_RIGHT_ARM_Y_OFFSET = 20
DRINK_SCENE_BARTENDER_HAND_SIZE = 10
DRINK_SCENE_BARTENDER_HAND_X_INSET = 1
DRINK_SCENE_BARTENDER_HAND_BOTTOM_OFFSET = 6
DRINK_SCENE_GRAB_HAND_WIDTH = 14
DRINK_SCENE_GRAB_HAND_HEIGHT = 17
DRINK_SCENE_GRAB_HAND_OVERLAP = 5
DRINK_SCENE_REACH_SHOULDER_X_OFFSET = -2
DRINK_SCENE_REACH_SHOULDER_Y_OFFSET = 30
DRINK_SCENE_PICKUP_PROGRESS_PORTION = 0.55
DRINK_SCENE_PICKUP_LIFT_Y = 18
DRINK_SCENE_PICKUP_PULL_X = 0
DRINK_SCENE_DRINK_HOLD_DURATION = 0.08
DRINK_SCENE_DRINK_RETURN_DURATION = 0.18
DRINK_SCENE_DRINK_MOUTH_X_OFFSET = 4
DRINK_SCENE_DRINK_MOUTH_Y_OFFSET = 18
DRINK_SCENE_BARTENDER_LEG_WIDTH = 14
DRINK_SCENE_BARTENDER_LEG_HEIGHT = 18
DRINK_SCENE_BARTENDER_LEG_GAP = 6
DRINK_SCENE_BARTENDER_HEAD_Y_OFFSET = 6
DRINK_SCENE_BARTENDER_HAT_WIDTH = 52
DRINK_SCENE_BARTENDER_HAT_HEIGHT = 24
DRINK_SCENE_BARTENDER_HAT_BRIM_HEIGHT = 4
DRINK_SCENE_BARTENDER_HAT_CROWN_INSET = 6
DRINK_SCENE_BARTENDER_HAT_Y_OFFSET = 7
DRINK_SCENE_BARTENDER_HAT_COLOR = pygame.Color("#2E2B25")
DRINK_SCENE_BARTENDER_BOWTIE_WIDTH = 18
DRINK_SCENE_BARTENDER_BOWTIE_HEIGHT = 10
DRINK_SCENE_BARTENDER_BOWTIE_CENTER = 6
DRINK_SCENE_BARTENDER_BOWTIE_Y = 14
DRINK_SCENE_BARTENDER_BOWTIE_COLOR = pygame.Color("#A3242B")
DRINK_SCENE_BARTENDER_GLASSES_WIDTH = 28
DRINK_SCENE_BARTENDER_GLASSES_HEIGHT = 8
DRINK_SCENE_BARTENDER_GLASSES_Y_OFFSET = 14
DRINK_SCENE_BARTENDER_GLASSES_BRIDGE = 4
DRINK_SCENE_BARTENDER_GLASSES_COLOR = pygame.Color("#3E2A1A")
DRINK_SCENE_BARTENDER_CIGAR_WIDTH = 14
DRINK_SCENE_BARTENDER_CIGAR_HEIGHT = 4
DRINK_SCENE_BARTENDER_CIGAR_Y_OFFSET = 24
DRINK_SCENE_BARTENDER_CIGAR_X_OFFSET = 10
DRINK_SCENE_BARTENDER_CIGAR_COLOR = pygame.Color("#6B4226")
DRINK_SCENE_BARTENDER_CIGAR_EMBER_COLOR = pygame.Color("#E85A1B")

# Shop offer tuning:
# Early shops should skew toward cheaper upgrades, while later shops
# open up pricier, stronger offers more often.
CHEAP_UPGRADE_COST_MAX = 3
MID_UPGRADE_COST_MAX = 5
EARLY_SHOP_LEVEL_MAX = 2
MID_SHOP_LEVEL_MAX = 4
EARLY_CHEAP_OFFER_WEIGHT_MULTIPLIER = 3.0
EARLY_MID_OFFER_WEIGHT_MULTIPLIER = 1.6
EARLY_EXPENSIVE_OFFER_WEIGHT_MULTIPLIER = 0.6
MID_CHEAP_OFFER_WEIGHT_MULTIPLIER = 1.8
MID_MID_OFFER_WEIGHT_MULTIPLIER = 1.6
MID_EXPENSIVE_OFFER_WEIGHT_MULTIPLIER = 1.1
LATE_CHEAP_OFFER_WEIGHT_MULTIPLIER = 1.0
LATE_MID_OFFER_WEIGHT_MULTIPLIER = 1.4
LATE_EXPENSIVE_OFFER_WEIGHT_MULTIPLIER = 2.0
EARLY_COSMETIC_OFFER_WEIGHT_MULTIPLIER = 0.35
MID_COSMETIC_OFFER_WEIGHT_MULTIPLIER = 0.55
LATE_COSMETIC_OFFER_WEIGHT_MULTIPLIER = 0.75
AFFORDABLE_OFFER_WEIGHT_MULTIPLIER = 1.2
NEAR_AFFORDABLE_COST_MARGIN = 2
NEAR_AFFORDABLE_OFFER_WEIGHT_MULTIPLIER = 1.05
LOW_LIFE_LAST_CALL_WEIGHT_MULTIPLIER = 3.0
MID_LIFE_LAST_CALL_WEIGHT_MULTIPLIER = 1.5
NO_GAMEPLAY_UPGRADES_WEIGHT_MULTIPLIER = 1.4
NO_COSMETICS_WEIGHT_MULTIPLIER = 1.3
HIGH_CASH_THRESHOLD = 10.0
HIGH_CASH_EXPENSIVE_COST_MIN = 6.0
HIGH_CASH_EXPENSIVE_WEIGHT_MULTIPLIER = 1.4
LOW_CASH_THRESHOLD = 3.0
LOW_CASH_CHEAP_COST_MAX = 3.0
LOW_CASH_CHEAP_WEIGHT_MULTIPLIER = 1.5

FAIL_OVERLAY_ALPHA = 80
GAME_OVER_OVERLAY_ALPHA = 170
FAIL_OVERLAY_COLOR = (32, 0, 0, FAIL_OVERLAY_ALPHA)
GAME_OVER_OVERLAY_COLOR = (0, 0, 0, GAME_OVER_OVERLAY_ALPHA)
FAIL_MESSAGE_Y = 156

# Cosmetic state ids:
# These are stored in run/round state so future cosmetic phases can stay data-driven.
GREEN_BEER_THEME_ID = "green_night"
WINE_BEER_THEME_ID = "wine_night"
HAT_COSMETIC_ID = "hat"
BOWTIE_COSMETIC_ID = "bowtie"
GLASSES_COSMETIC_ID = "glasses"
CIGAR_COSMETIC_ID = "cigar"

# Temporary testing override:
# A fresh run starts with these cosmetics for the opening round only.
ENABLE_FIRST_ROUND_COSMETIC_TEST = True


class FlowState(Enum):
    PLAYING = auto()
    FAILING = auto()
    LEVEL_CLEAR_DRINK_SCENE = auto()
    GAME_OVER = auto()


@dataclass(frozen=True)
class LevelConfig:
    target_serves: int
    spawn_interval: float
    min_walk_speed: float
    max_walk_speed: float
    long_shove_weight: float
    offscreen_shove_weight: float
    short_shove_weight: float


@dataclass(frozen=True)
class UpgradeDefinition:
    id: str
    name: str
    description: str
    effect_type: str
    base_cost: float
    cost_per_level: float
    base_bonus: float
    bonus_per_level: float
    min_level: int = 1
    max_stacks: int = 99
    weight: float = 1.0
    is_cosmetic: bool = False


@dataclass(frozen=True)
class UpgradeOffer:
    definition: UpgradeDefinition
    level: int
    owned_stacks: int

    @property
    def cost(self) -> float:
        raw_cost = self.definition.base_cost + ((self.level - 1) * self.definition.cost_per_level)
        return max(0.0, float(int(raw_cost + 0.5)))

    @property
    def bonus(self) -> float:
        bonus_steps = (self.level - 1) // 2
        return self.definition.base_bonus + (bonus_steps * self.definition.bonus_per_level)

    @property
    def can_offer(self) -> bool:
        return self.level >= self.definition.min_level and self.owned_stacks < self.definition.max_stacks


@dataclass(frozen=True)
class DrinkSceneSlot:
    kind: str
    offer: UpgradeOffer | None = None


@dataclass
class RunModifiers:
    quick_pour_fill_duration_delta: float = 0.0
    fast_serve_speed_bonus: float = 0.0
    quick_feet_speed_bonus: float = 0.0
    long_reach_padding_bonus: int = 0
    lucky_tips_chance_bonus: float = 0.0
    bigger_tips_cash_bonus: float = 0.0


QUICK_POUR_UPGRADE = UpgradeDefinition(
    id="quick_pour",
    name="Quicker Pour",
    description="Fill beers faster.",
    effect_type="quick_pour",
    base_cost=3.0,
    cost_per_level=2.5,
    base_bonus=0.075,
    bonus_per_level=0.075,
    min_level=1,
    max_stacks=6,
    weight=4,
)

FAST_SERVE_UPGRADE = UpgradeDefinition(
    id="fast_serve",
    name="Faster Serve",
    description="Launch beers faster.",
    effect_type="fast_serve",
    base_cost=3.0,
    cost_per_level=2.5,
    base_bonus=0.075,
    bonus_per_level=0.075,
    min_level=1,
    max_stacks=6,
    weight=4,
)

QUICK_FEET_UPGRADE = UpgradeDefinition(
    id="quick_feet",
    name="Quicker Feet",
    description="Move faster between catches and pours.",
    effect_type="quick_feet",
    base_cost=4.5,
    cost_per_level=2.5,
    base_bonus=0.075,
    bonus_per_level=0.075,
    min_level=1,
    max_stacks=6,
    weight=3,
)

LONG_REACH_UPGRADE = UpgradeDefinition(
    id="long_reach",
    name="Longer Reach",
    description="Catch empties with a wider reach.",
    effect_type="long_reach",
    base_cost=6.0,
    cost_per_level=2.5,
    base_bonus=0.075,
    bonus_per_level=0.075,
    min_level=2,
    max_stacks=6,
    weight=2,
)

LUCKY_TIPS_UPGRADE = UpgradeDefinition(
    id="lucky_tips",
    name="Lucky Tips",
    description="Increase tip drop chance for the next round.",
    effect_type="lucky_tips",
    base_cost=6.0,
    cost_per_level=2.5,
    base_bonus=0.075,
    bonus_per_level=0.075,
    min_level=2,
    max_stacks=99,
    weight=3,
)

BIGGER_TIPS_UPGRADE = UpgradeDefinition(
    id="bigger_tips",
    name="Bigger Tips",
    description="Each tip is worth more cash for the next round.",
    effect_type="bigger_tips",
    base_cost=7.5,
    cost_per_level=4.5,
    base_bonus=0.0,
    bonus_per_level=1.5,
    min_level=3,
    max_stacks=99,
    weight=2,
)

LAST_CALL_UPGRADE = UpgradeDefinition(
    id="last_call",
    name="Last Call",
    description="Gain an extra life.",
    effect_type="last_call",
    base_cost=5.0,
    cost_per_level=1.0,
    base_bonus=0.0,
    bonus_per_level=0.0,
    min_level=1,
    max_stacks=2,
    weight=3,
)

GREEN_NIGHT_UPGRADE = UpgradeDefinition(
    id="green_night",
    name="Green Night",
    description="Next round pours bright green beer.",
    effect_type="green_night",
    base_cost=3,
    cost_per_level=1,
    base_bonus=0.0,
    bonus_per_level=0.0,
    min_level=1,
    max_stacks=99,
    weight=1.4,
    is_cosmetic=True,
)

WINE_NIGHT_UPGRADE = UpgradeDefinition(
    id="wine_night",
    name="Wine Night",
    description="Next round pours deep red wine-colored drinks.",
    effect_type="wine_night",
    base_cost=3,
    cost_per_level=1,
    base_bonus=0.0,
    bonus_per_level=0.0,
    min_level=1,
    max_stacks=99,
    weight=1.4,
    is_cosmetic=True,
)

HAT_UPGRADE = UpgradeDefinition(
    id="hat",
    name="Hat",
    description="Bartender wears a hat for the rest of the run.",
    effect_type="hat",
    base_cost=4,
    cost_per_level=1,
    base_bonus=0.0,
    bonus_per_level=0.0,
    min_level=1,
    max_stacks=1,
    weight=1,
    is_cosmetic=True,
)

BOWTIE_UPGRADE = UpgradeDefinition(
    id="bowtie",
    name="Bowtie",
    description="Bartender wears a bowtie for the rest of the run.",
    effect_type="bowtie",
    base_cost=4,
    cost_per_level=1,
    base_bonus=0.0,
    bonus_per_level=0.0,
    min_level=1,
    max_stacks=1,
    weight=1,
    is_cosmetic=True,
)

GLASSES_UPGRADE = UpgradeDefinition(
    id="glasses",
    name="Glasses",
    description="Bartender wears glasses for the rest of the run.",
    effect_type="glasses",
    base_cost=4,
    cost_per_level=1,
    base_bonus=0.0,
    bonus_per_level=0.0,
    min_level=1,
    max_stacks=1,
    weight=1,
    is_cosmetic=True,
)

CIGAR_UPGRADE = UpgradeDefinition(
    id="cigar",
    name="Cigar",
    description="Bartender smokes a cigar for the rest of the run.",
    effect_type="cigar",
    base_cost=5,
    cost_per_level=1,
    base_bonus=0.0,
    bonus_per_level=0.0,
    min_level=1,
    max_stacks=1,
    weight=1,
    is_cosmetic=True,
)

GAMEPLAY_UPGRADE_DEFINITIONS = (
    QUICK_POUR_UPGRADE,
    FAST_SERVE_UPGRADE,
    QUICK_FEET_UPGRADE,
    LONG_REACH_UPGRADE,
    LUCKY_TIPS_UPGRADE,
    BIGGER_TIPS_UPGRADE,
    LAST_CALL_UPGRADE,
)

COSMETIC_UPGRADE_DEFINITIONS = (
    GREEN_NIGHT_UPGRADE,
    WINE_NIGHT_UPGRADE,
    HAT_UPGRADE,
    BOWTIE_UPGRADE,
    GLASSES_UPGRADE,
    CIGAR_UPGRADE,
)

ALL_UPGRADE_DEFINITIONS = GAMEPLAY_UPGRADE_DEFINITIONS + COSMETIC_UPGRADE_DEFINITIONS

# Live shop pool now includes both gameplay and cosmetic upgrades.
UPGRADE_DEFINITIONS = ALL_UPGRADE_DEFINITIONS


def build_level_config(level_number: int) -> LevelConfig:
    level = max(1, level_number)
    if level == 1:
        shove_weights = LEVEL_ONE_SHOVE_WEIGHTS
    elif level == 2:
        shove_weights = LEVEL_TWO_SHOVE_WEIGHTS
    else:
        shove_weights = LEVEL_THREE_PLUS_SHOVE_WEIGHTS

    return LevelConfig(
        target_serves=LEVEL_ONE_TARGET_SERVES + (((level - 1) // LEVEL_TARGET_STEP_INTERVAL) * LEVEL_TARGET_STEP_AMOUNT),
        spawn_interval=max(MIN_SPAWN_INTERVAL, LEVEL_ONE_SPAWN_INTERVAL - ((level - 1) * LEVEL_SPAWN_INTERVAL_STEP)),
        min_walk_speed=LEVEL_ONE_MIN_WALK_SPEED + ((level - 1) * LEVEL_MIN_WALK_SPEED_STEP),
        max_walk_speed=LEVEL_ONE_MAX_WALK_SPEED + ((level - 1) * LEVEL_MAX_WALK_SPEED_STEP),
        long_shove_weight=shove_weights[0],
        offscreen_shove_weight=shove_weights[1],
        short_shove_weight=shove_weights[2],
    )


class Game:
    PATRON_SPAWN_X = -Patron.BODY_WIDTH

    def __init__(self) -> None:
        self.scene_renderer = SceneRenderer()
        self.hud_renderer = HUDRenderer()
        self.overlay_font = pygame.font.SysFont("couriernew", 18, bold=True)
        self.detail_font = pygame.font.SysFont("couriernew", 12, bold=True)
        self.drink_scene_title_font = pygame.font.SysFont("couriernew", 20, bold=True)
        self.drink_scene_detail_font = pygame.font.SysFont("couriernew", 14, bold=True)
        self._reset_game()

    @staticmethod
    def _format_cash(amount: float) -> str:
        return f"${amount:0.2f}"

    @staticmethod
    def _format_cash_shortfall(amount: float) -> str:
        return f"NEED ${amount:0.2f}"

    @staticmethod
    def _format_offer_cash(amount: float) -> str:
        if float(amount).is_integer():
            return f"${int(amount)}"
        if abs((amount * 2) - round(amount * 2)) < 1e-9:
            return f"${amount:.1f}"
        return f"${amount:.2f}"

    @staticmethod
    def _format_percent_bonus(bonus: float) -> str:
        percent = bonus * 100
        if abs(percent - round(percent)) < 1e-9:
            return f"+{int(round(percent))}%"
        return f"+{percent:.1f}%"

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.flow_state is FlowState.FAILING:
            return

        if self.flow_state is FlowState.GAME_OVER:
            if event.type == pygame.KEYDOWN:
                self._reset_game()
            return

        if self.flow_state is FlowState.LEVEL_CLEAR_DRINK_SCENE:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self._is_drink_scene_drinking():
                        self.drink_scene_space_held = True
                    else:
                        self._start_drink_scene_drink()
                elif self._is_drink_scene_drinking():
                    return
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self._move_drink_scene_selection(-1)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._move_drink_scene_selection(1)
            elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                self._pause_drink_scene_drink()
            return

        if event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
            self.bartender.release_pour()
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_SPACE:
            self.bartender.start_pour()
            return

        is_arrow = event.key in (
            pygame.K_UP,
            pygame.K_DOWN,
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_a,
            pygame.K_d,
            pygame.K_w,
            pygame.K_s,
        )
        if is_arrow and self.bartender.is_pouring:
            self.bartender.cancel_pour()

        if event.key in (pygame.K_UP, pygame.K_w):
            self.bartender.move_up()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.bartender.move_down()

    def update(self, dt: float) -> None:
        if self.flow_state is FlowState.FAILING:
            self.fail_feedback_timer = max(0.0, self.fail_feedback_timer - dt)
            if self.fail_feedback_timer == 0.0:
                self._finish_fail_feedback()
            return

        if self.flow_state is FlowState.LEVEL_CLEAR_DRINK_SCENE:
            self._update_drink_scene_drink(dt)
            return

        if self.flow_state is FlowState.GAME_OVER:
            return

        if not self.bartender.is_pouring:
            pressed = pygame.key.get_pressed()
            moving_left = pressed[pygame.K_LEFT] or pressed[pygame.K_a]
            moving_right = pressed[pygame.K_RIGHT] or pressed[pygame.K_d]
            if moving_left and not moving_right:
                self.bartender.walk_left(dt)
            elif moving_right and not moving_left:
                self.bartender.walk_right(dt)
            else:
                self.bartender.stop_walking()
        else:
            self.bartender.stop_walking()

        self._spawn_patrons(dt)
        self._update_patrons(dt)
        self._update_returning_glasses(dt)
        self._spawn_returning_glasses()
        self._collect_tips()
        self._handle_return_glass_catches()
        self.bartender.update_pour(dt)
        if self._resolve_round_failures():
            return

        self._handle_serves()
        if self.flow_state is FlowState.LEVEL_CLEAR_DRINK_SCENE:
            return

    def draw(self, surface: pygame.Surface) -> None:
        if self.flow_state is FlowState.FAILING:
            frame_surface = pygame.Surface(surface.get_size())
            self._draw_frame(frame_surface)
            shake_x, shake_y = self._fail_shake_offset()
            surface.fill((0, 0, 0))
            surface.blit(frame_surface, (shake_x, shake_y))
            self._draw_fail_overlay(surface)
            return

        if self.flow_state is FlowState.LEVEL_CLEAR_DRINK_SCENE:
            self._draw_level_clear_drink_scene(surface)
            return

        self._draw_frame(surface)

    def _draw_frame(self, surface: pygame.Surface) -> None:
        beer_fill_color = self._active_beer_fill_color()
        self.scene_renderer.draw_scene_backdrop(surface)
        for patron in reversed(self.patrons):
            patron.draw(surface)
        self.scene_renderer.draw_bar_fronts(surface)
        for patron in reversed(self.patrons):
            patron.draw_held_glass(surface, fill_color=beer_fill_color)
        for tip in self.tips:
            tip.draw(surface)
        for returning_glass in self.returning_glasses:
            returning_glass.draw(surface)
        self.bartender.draw_flying_glasses(surface, fill_color=beer_fill_color)
        self.bartender.draw(surface)
        self.bartender.draw_tap_glass(surface, fill_color=beer_fill_color)
        self.bartender.draw_serve_visual(surface, fill_color=beer_fill_color)
        self.hud_renderer.draw(
            surface,
            lives=self.lives,
            current_level=self.current_level,
            served=self.served_count,
            target=self.level_config.target_serves,
            cash_text=self._format_cash(self.cash),
            score=self.score,
        )
        if self.flow_state is FlowState.GAME_OVER:
            self._draw_game_over_overlay(surface)

    def _handle_serves(self) -> None:
        active_glasses = []
        for flying_glass in self.bartender.flying_glasses:
            frontmost_patron = self._frontmost_receivable_patron(flying_glass.bar_index)
            if (
                frontmost_patron is not None
                and frontmost_patron.can_receive_beer
                and flying_glass.rect.colliderect(frontmost_patron.body_rect)
            ):
                self._maybe_spawn_tip(frontmost_patron, flying_glass)
                frontmost_patron.receive_beer(flying_glass.fill_ratio)
                self.score += BEER_SERVED_SCORE
                self.cash += BEER_SERVED_CASH
                self.served_count += 1
                if self.served_count >= self.level_config.target_serves:
                    self._enter_level_clear()
                continue
            active_glasses.append(flying_glass)

        self.bartender.flying_glasses = active_glasses

    def _update_patrons(self, dt: float) -> None:
        for bar_index in range(BAR_COUNT):
            lane_patrons = [patron for patron in self.patrons if patron.bar_index == bar_index]
            for patron in lane_patrons:
                if not patron.can_receive_beer:
                    patron.update(dt)

            for patron in lane_patrons:
                if patron.can_receive_beer:
                    patron.update(dt)

    def _frontmost_receivable_patron(self, bar_index: int) -> Patron | None:
        receivable_patrons = [
            patron
            for patron in self.patrons
            if patron.bar_index == bar_index and patron.can_receive_beer
        ]
        if not receivable_patrons:
            return None
        return max(receivable_patrons, key=lambda patron: patron.x)

    def _spawn_patrons(self, dt: float) -> None:
        self.spawn_timer += dt
        while self.spawn_timer >= self.level_config.spawn_interval:
            self.spawn_timer -= self.level_config.spawn_interval
            self._spawn_next_patron()

    def _spawn_next_patron(self) -> None:
        for offset in range(BAR_COUNT):
            bar_index = (self.next_spawn_bar + offset) % BAR_COUNT
            lane_patrons = [patron for patron in self.patrons if patron.bar_index == bar_index]
            if len(lane_patrons) >= MAX_PATRONS_PER_LANE:
                continue
            if not self._lane_has_spawn_room(lane_patrons):
                continue

            archetype = self.patron_rng.choice(PATRON_ARCHETYPES)
            base_walk_speed = self.patron_rng.uniform(
                self.level_config.min_walk_speed,
                self.level_config.max_walk_speed,
            )
            base_drink_duration = self.patron_rng.uniform(
                MIN_DRINK_DURATION,
                MAX_DRINK_DURATION,
            )
            self.patrons.append(
                Patron(
                    bar_index=bar_index,
                    start_x=float(self.PATRON_SPAWN_X),
                    walk_speed=base_walk_speed * archetype.walk_speed_multiplier,
                    drink_duration=base_drink_duration * archetype.drink_duration_multiplier,
                    archetype=archetype,
                    shove_weights=(
                        self.level_config.long_shove_weight,
                        self.level_config.offscreen_shove_weight,
                        self.level_config.short_shove_weight,
                    ),
                )
            )
            self.next_spawn_bar = (bar_index + 1) % BAR_COUNT
            return

    def _lane_has_spawn_room(self, lane_patrons: list[Patron]) -> bool:
        blocking_patrons = [
            patron for patron in lane_patrons if patron.blocks_spawn_entry
        ]
        if not blocking_patrons:
            return True

        spawn_clear_x = self.PATRON_SPAWN_X + Patron.BODY_WIDTH + Patron.QUEUE_GAP
        return all(patron.x >= spawn_clear_x for patron in blocking_patrons)

    def _handle_return_glass_catches(self) -> None:
        active_returning_glasses: list[ReturningGlass] = []
        for returning_glass in self.returning_glasses:
            if returning_glass.bar_index != self.bartender.bar_index:
                active_returning_glasses.append(returning_glass)
                continue
            if returning_glass.rect.colliderect(self.bartender.catch_rect):
                continue
            active_returning_glasses.append(returning_glass)
        self.returning_glasses = active_returning_glasses

    def _spawn_returning_glasses(self) -> None:
        for patron in self.patrons:
            returning_glass = patron.consume_pending_returning_glass()
            if returning_glass is not None:
                self.returning_glasses.append(returning_glass)

    def _update_returning_glasses(self, dt: float) -> None:
        active_returning_glasses: list[ReturningGlass] = []
        for returning_glass in self.returning_glasses:
            returning_glass.update(dt)
            if returning_glass.is_offscreen:
                self.missed_return_glass = True
                continue
            active_returning_glasses.append(returning_glass)
        self.returning_glasses = active_returning_glasses

    def _maybe_spawn_tip(self, patron: Patron, flying_glass) -> None:
        if self.tip_rng.random() > self._effective_tip_chance(patron):
            return
        tip_x = float(flying_glass.rect.centerx - (Tip.WIDTH / 2))
        self.tips.append(Tip(x=tip_x, bar_index=patron.bar_index))

    def _collect_tips(self) -> None:
        active_tips: list[Tip] = []
        for tip in self.tips:
            if (
                tip.bar_index == self.bartender.bar_index
                and tip.rect.colliderect(self.bartender.body_rect)
            ):
                self.score += TIP_SCORE
                self.tip_score += TIP_SCORE
                self.cash += self._effective_tip_cash_reward()
                self.tips_collected += 1
                continue
            active_tips.append(tip)
        self.tips = active_tips

    def _resolve_round_failures(self) -> bool:
        fail_reason: str | None = None
        if self.missed_return_glass:
            fail_reason = "MISSED GLASS"
        elif self.bartender.consume_missed_flying_glass():
            fail_reason = "MISSED BEER"
        self.missed_return_glass = False
        for patron in self.patrons:
            if patron.consume_hit_tap_wall():
                fail_reason = "PATRON REACHED TAP"
                break

        if fail_reason is None:
            return False

        self._lose_life(fail_reason)
        return True

    def _lose_life(self, fail_reason: str) -> None:
        self._clear_active_round_beer_theme()
        self._clear_active_round_tip_modifiers()
        self.lives = max(0, self.lives - 1)
        self.fail_message = fail_reason
        self.fail_feedback_timer = FAIL_FEEDBACK_DURATION
        self.pending_game_over = self.lives == 0
        self.flow_state = FlowState.FAILING

    def _reset_round(self) -> None:
        self.bartender = Bartender()
        self._apply_round_cosmetic_state()
        self._apply_run_modifiers_to_bartender()
        self.patrons = []
        self.tips = []
        self.returning_glasses = []
        self.missed_return_glass = False
        self.spawn_timer = max(0.0, self.level_config.spawn_interval - FIRST_PATRON_DELAY)
        self.next_spawn_bar = self.patron_rng.randrange(BAR_COUNT)
        self.fail_feedback_timer = 0.0
        self.fail_message = None
        self.pending_game_over = False
        self.flow_state = FlowState.PLAYING

    def _reset_game(self) -> None:
        self.current_level = 1
        self.level_config = build_level_config(self.current_level)
        self.lives = STARTING_LIVES
        self.cash = STARTING_CASH
        self.score = 0
        self.run_modifiers = RunModifiers()
        self.run_bartender_has_hat = False
        self.run_bartender_has_bowtie = False
        self.run_bartender_has_glasses = False
        self.run_bartender_has_cigar = False
        self.pending_next_round_beer_theme: str | None = None
        self.active_round_beer_theme: str | None = None
        self.pending_next_round_lucky_tips_chance_bonus = 0.0
        self.active_round_lucky_tips_chance_bonus = 0.0
        self.pending_next_round_bigger_tips_cash_bonus = 0.0
        self.active_round_bigger_tips_cash_bonus = 0.0
        self.round_bartender_has_hat = False
        self.round_bartender_has_bowtie = False
        self.round_bartender_has_glasses = False
        self.round_bartender_has_cigar = False
        self.first_round_cosmetic_test_pending = ENABLE_FIRST_ROUND_COSMETIC_TEST
        self.upgrade_stacks = {upgrade.id: 0 for upgrade in UPGRADE_DEFINITIONS}
        self.upgrade_definitions = UPGRADE_DEFINITIONS
        self.drink_scene_slots: list[DrinkSceneSlot] = []
        self.drink_scene_selected_index = 0
        self.drink_scene_purchased_indices: set[int] = set()
        self.drink_scene_active_index: int | None = None
        self.drink_scene_drink_progress = 0.0
        self.drink_scene_space_held = False
        self.drink_scene_hold_timer = 0.0
        self.drink_scene_return_progress = 0.0
        self.flow_state = FlowState.PLAYING
        self.drink_scene_summary: dict[str, int | float] | None = None
        self.patron_rng = build_walk_speed_rng()
        self.tip_rng = Random(TIP_RNG_SEED)
        self._reset_level_progress()
        self._reset_round()

    def _advance_to_next_round(self) -> None:
        self.current_level += 1
        self.level_config = build_level_config(self.current_level)
        self._activate_pending_round_beer_theme()
        self._activate_pending_round_tip_modifiers()
        self.drink_scene_summary = None
        self.drink_scene_slots = []
        self.drink_scene_selected_index = 0
        self.drink_scene_purchased_indices = set()
        self._clear_drink_scene_drink()
        self.flow_state = FlowState.PLAYING
        self._reset_level_progress()
        self._reset_round()

    def _reset_level_progress(self) -> None:
        self.served_count = 0
        self.tips_collected = 0
        self.tip_score = 0

    def _enter_level_clear(self) -> None:
        if self.flow_state is FlowState.LEVEL_CLEAR_DRINK_SCENE:
            return

        self._clear_active_round_beer_theme()
        self._clear_active_round_tip_modifiers()
        beer_score = self.served_count * BEER_SERVED_SCORE
        tips_score = self.tip_score
        lives_bonus = self.lives * LIVES_REMAINING_BONUS
        self.score += lives_bonus
        self.flow_state = FlowState.LEVEL_CLEAR_DRINK_SCENE
        self.drink_scene_slots = self._build_drink_scene_slots()
        self.drink_scene_selected_index = 0
        self.drink_scene_purchased_indices = set()
        self._clear_drink_scene_drink()
        self.drink_scene_summary = {
            "level": self.current_level,
            "beer_score": beer_score,
            "tips_score": tips_score,
            "lives_bonus": lives_bonus,
            "cash": self.cash,
            "total_score": self.score,
        }

    def _draw_game_over_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(GAME_OVER_OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))

        title = self.overlay_font.render("GAME OVER", True, OVERLAY_TEXT_COLOR)
        prompt = self.detail_font.render(
            "PRESS ANY KEY TO RESTART",
            True,
            OVERLAY_TEXT_COLOR,
        )

        title_rect = title.get_rect(center=(surface.get_width() // 2, GAME_OVER_TITLE_Y))
        prompt_rect = prompt.get_rect(center=(surface.get_width() // 2, GAME_OVER_PROMPT_Y))
        surface.blit(title, title_rect)
        surface.blit(prompt, prompt_rect)

    def _draw_level_clear_drink_scene(self, surface: pygame.Surface) -> None:
        summary = self.drink_scene_summary
        if summary is None:
            return

        surface.fill(DRINK_SCENE_BACKGROUND_COLOR)
        center_x = surface.get_width() // 2

        self._draw_drink_scene_sign(surface, center_x, int(summary["level"]))
        self._draw_drink_scene_cash(surface, center_x)
        self._draw_drink_scene_bar_back(surface, center_x)
        self._draw_drink_scene_bartender(surface, center_x)
        self._draw_drink_scene_bar_front(surface, center_x)
        self._draw_drink_scene_slots(surface, center_x)
        selected_index = self.drink_scene_active_index if self.drink_scene_active_index is not None else self.drink_scene_selected_index
        if 0 <= selected_index < len(self.drink_scene_slots):
            bartender_body_rect = self._drink_scene_bartender_body_rect(center_x)
            active_mug_rect, _ = self._drink_scene_slot_geometry(
                center_x,
                selected_index,
                bartender_body_rect,
            )
            self._draw_drink_scene_grab_hand(surface, active_mug_rect)

    def _drink_scene_selected_slot_center_x(self, center_x: int) -> int | None:
        if not self.drink_scene_slots:
            return None
        return self._drink_scene_slot_center_x(center_x, self.drink_scene_selected_index)

    def _drink_scene_slot_center_x(self, center_x: int, index: int) -> int:
        start_x = center_x - DRINK_SCENE_SLOT_SPACING
        return start_x + (index * DRINK_SCENE_SLOT_SPACING)

    def _drink_scene_bartender_center_x(self, center_x: int) -> int:
        selected_slot_center_x = self._drink_scene_selected_slot_center_x(center_x)
        if selected_slot_center_x is None:
            return center_x
        return selected_slot_center_x + DRINK_SCENE_BARTENDER_SLOT_CENTER_OFFSET

    def _drink_scene_sign_rect(self, center_x: int) -> pygame.Rect:
        sign_rect = pygame.Rect(0, 0, DRINK_SCENE_SIGN_WIDTH, DRINK_SCENE_SIGN_HEIGHT)
        sign_rect.center = (center_x, DRINK_SCENE_SIGN_Y)
        return sign_rect

    def _drink_scene_bar_rect(self, center_x: int) -> pygame.Rect:
        return pygame.Rect(
            center_x - (DRINK_SCENE_BAR_WIDTH // 2),
            DRINK_SCENE_BAR_Y,
            DRINK_SCENE_BAR_WIDTH,
            DRINK_SCENE_BAR_HEIGHT,
        )

    def _drink_scene_bartender_body_rect(self, center_x: int) -> pygame.Rect:
        bartender_center_x = self._drink_scene_bartender_center_x(center_x)
        body_bottom = DRINK_SCENE_BAR_Y + DRINK_SCENE_BARTENDER_BODY_BOTTOM_OFFSET
        return pygame.Rect(
            bartender_center_x - (DRINK_SCENE_BARTENDER_BODY_WIDTH // 2),
            body_bottom - DRINK_SCENE_BARTENDER_BODY_HEIGHT,
            DRINK_SCENE_BARTENDER_BODY_WIDTH,
            DRINK_SCENE_BARTENDER_BODY_HEIGHT,
        )

    def _drink_scene_pickup_fraction(self, index: int) -> float:
        if self.drink_scene_active_index != index:
            return 0.0
        return min(1.0, self.drink_scene_drink_progress / DRINK_SCENE_PICKUP_PROGRESS_PORTION)

    def _drink_scene_grab_hand_rect(self, target_rect: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(
            target_rect.left - (DRINK_SCENE_GRAB_HAND_WIDTH - DRINK_SCENE_GRAB_HAND_OVERLAP),
            target_rect.centery - (DRINK_SCENE_GRAB_HAND_HEIGHT // 2),
            DRINK_SCENE_GRAB_HAND_WIDTH,
            DRINK_SCENE_GRAB_HAND_HEIGHT,
        )

    def _drink_scene_slot_geometry(
        self,
        center_x: int,
        index: int,
        bartender_body_rect: pygame.Rect | None = None,
    ) -> tuple[pygame.Rect, float]:
        slot_center_x = self._drink_scene_slot_center_x(center_x, index)
        slot_center_y = DRINK_SCENE_SLOT_Y + (DRINK_SCENE_SLOT_HEIGHT // 2)

        mug_center_x = float(slot_center_x)
        mug_center_y = float(slot_center_y)
        fill_ratio = 1.0

        if self.drink_scene_active_index == index and bartender_body_rect is not None:
            mouth_center_y = float(bartender_body_rect.top + DRINK_SCENE_DRINK_MOUTH_Y_OFFSET)
            if self.drink_scene_drink_progress >= 1.0:
                return_t = self.drink_scene_return_progress
                mug_center_x = float(slot_center_x)
                mug_center_y = mouth_center_y + ((slot_center_y - mouth_center_y) * return_t)
                fill_ratio = 0.0
            else:
                pickup_t = self._drink_scene_pickup_fraction(index)
                mug_center_x = float(slot_center_x)
                mug_center_y = slot_center_y + ((mouth_center_y - slot_center_y) * pickup_t)
                fill_ratio = max(0.0, 1.0 - self.drink_scene_drink_progress)

        mug_rect = pygame.Rect(
            round(mug_center_x - (DRINK_SCENE_SLOT_WIDTH / 2)),
            round(mug_center_y - (DRINK_SCENE_SLOT_HEIGHT / 2)),
            DRINK_SCENE_SLOT_WIDTH,
            DRINK_SCENE_SLOT_HEIGHT,
        )
        return mug_rect, fill_ratio

    def _draw_drink_scene_sign(self, surface: pygame.Surface, center_x: int, level_number: int) -> None:
        sign_rect = self._drink_scene_sign_rect(center_x)
        glow_rect = sign_rect.inflate(DRINK_SCENE_SIGN_GLOW_INFLATE, DRINK_SCENE_SIGN_GLOW_INFLATE)
        pygame.draw.rect(surface, DRINK_SCENE_SIGN_GLOW_COLOR, glow_rect, border_radius=DRINK_SCENE_SIGN_GLOW_RADIUS)
        pygame.draw.rect(
            surface,
            DRINK_SCENE_BACKGROUND_COLOR,
            glow_rect.inflate(-DRINK_SCENE_SIGN_BACKGROUND_INSET, -DRINK_SCENE_SIGN_BACKGROUND_INSET),
            border_radius=DRINK_SCENE_SIGN_FRAME_RADIUS,
        )
        pygame.draw.rect(surface, DRINK_SCENE_SIGN_FRAME_COLOR, sign_rect, border_radius=DRINK_SCENE_SIGN_FRAME_RADIUS)
        pygame.draw.rect(
            surface,
            DRINK_SCENE_SIGN_GLOW_COLOR,
            sign_rect.inflate(-DRINK_SCENE_SIGN_INNER_FRAME_INSET, -DRINK_SCENE_SIGN_INNER_FRAME_INSET),
            DRINK_SCENE_SIGN_INNER_FRAME_WIDTH,
            border_radius=DRINK_SCENE_SIGN_INNER_FRAME_RADIUS,
        )

        title_surface = self.drink_scene_title_font.render(
            f"LEVEL {level_number:02d} COMPLETE!",
            True,
            DRINK_SCENE_SIGN_TEXT_COLOR,
        )
        surface.blit(title_surface, title_surface.get_rect(center=sign_rect.center))

    def _draw_drink_scene_cash(self, surface: pygame.Surface, center_x: int) -> None:
        sign_rect = self._drink_scene_sign_rect(center_x)
        cash_surface = self.drink_scene_detail_font.render(
            f"CASH {self._format_cash(self.cash)}",
            True,
            OVERLAY_TEXT_COLOR,
        )
        cash_rect = cash_surface.get_rect()
        cash_rect.topright = (
            sign_rect.right + DRINK_SCENE_CASH_X_OFFSET,
            sign_rect.bottom + DRINK_SCENE_CASH_Y_OFFSET,
        )
        surface.blit(cash_surface, cash_rect)

    def _draw_drink_scene_bar_back(self, surface: pygame.Surface, center_x: int) -> None:
        return

    def _draw_drink_scene_bar_front(self, surface: pygame.Surface, center_x: int) -> None:
        bar_rect = self._drink_scene_bar_rect(center_x)
        top_rect = pygame.Rect(
            bar_rect.left,
            bar_rect.top,
            bar_rect.width,
            DRINK_SCENE_BAR_TOP_HEIGHT,
        )
        front_rect = pygame.Rect(
            bar_rect.left,
            bar_rect.top + DRINK_SCENE_BAR_TOP_HEIGHT,
            bar_rect.width,
            bar_rect.height - DRINK_SCENE_BAR_TOP_HEIGHT,
        )
        trim_rect = pygame.Rect(
            bar_rect.left,
            bar_rect.bottom - DRINK_SCENE_BAR_TRIM_HEIGHT,
            bar_rect.width,
            DRINK_SCENE_BAR_TRIM_HEIGHT,
        )

        pygame.draw.rect(surface, DRINK_SCENE_BAR_TOP_COLOR, top_rect)
        pygame.draw.line(
            surface,
            DRINK_SCENE_SIGN_FRAME_COLOR,
            (top_rect.left, top_rect.bottom),
            (top_rect.right, top_rect.bottom),
            DRINK_SCENE_BAR_DIVIDER_LINE_WIDTH,
        )
        pygame.draw.rect(surface, DRINK_SCENE_BAR_FRONT_COLOR, front_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BAR_TRIM_COLOR, trim_rect)

    def _draw_drink_scene_bartender(self, surface: pygame.Surface, center_x: int) -> None:
        body_rect = self._drink_scene_bartender_body_rect(center_x)
        head_rect = pygame.Rect(
            body_rect.centerx - (DRINK_SCENE_BARTENDER_HEAD_SIZE // 2),
            body_rect.top - DRINK_SCENE_BARTENDER_HEAD_SIZE + DRINK_SCENE_BARTENDER_HEAD_Y_OFFSET,
            DRINK_SCENE_BARTENDER_HEAD_SIZE,
            DRINK_SCENE_BARTENDER_HEAD_SIZE,
        )
        left_arm_rect = pygame.Rect(
            body_rect.left + DRINK_SCENE_BARTENDER_LEFT_ARM_X_OFFSET,
            body_rect.top + DRINK_SCENE_BARTENDER_LEFT_ARM_Y_OFFSET,
            DRINK_SCENE_BARTENDER_ARM_WIDTH,
            DRINK_SCENE_BARTENDER_ARM_HEIGHT,
        )
        right_arm_rect = pygame.Rect(
            body_rect.right + DRINK_SCENE_BARTENDER_RIGHT_ARM_X_OFFSET,
            body_rect.top + DRINK_SCENE_BARTENDER_RIGHT_ARM_Y_OFFSET,
            DRINK_SCENE_BARTENDER_ARM_WIDTH,
            DRINK_SCENE_BARTENDER_ARM_HEIGHT,
        )
        apron_rect = pygame.Rect(
            body_rect.centerx - (DRINK_SCENE_BARTENDER_APRON_WIDTH // 2),
            body_rect.top + DRINK_SCENE_BARTENDER_APRON_Y,
            DRINK_SCENE_BARTENDER_APRON_WIDTH,
            body_rect.height - (DRINK_SCENE_BARTENDER_APRON_Y + DRINK_SCENE_BARTENDER_APRON_BOTTOM_PADDING),
        )
        left_leg_rect = pygame.Rect(
            body_rect.centerx - DRINK_SCENE_BARTENDER_LEG_GAP - DRINK_SCENE_BARTENDER_LEG_WIDTH,
            body_rect.bottom - DRINK_SCENE_BARTENDER_LEG_HEIGHT,
            DRINK_SCENE_BARTENDER_LEG_WIDTH,
            DRINK_SCENE_BARTENDER_LEG_HEIGHT,
        )
        right_leg_rect = pygame.Rect(
            body_rect.centerx + DRINK_SCENE_BARTENDER_LEG_GAP,
            body_rect.bottom - DRINK_SCENE_BARTENDER_LEG_HEIGHT,
            DRINK_SCENE_BARTENDER_LEG_WIDTH,
            DRINK_SCENE_BARTENDER_LEG_HEIGHT,
        )
        left_hand_rect = pygame.Rect(
            left_arm_rect.left + DRINK_SCENE_BARTENDER_HAND_X_INSET,
            left_arm_rect.bottom - DRINK_SCENE_BARTENDER_HAND_BOTTOM_OFFSET,
            DRINK_SCENE_BARTENDER_HAND_SIZE,
            DRINK_SCENE_BARTENDER_HAND_SIZE,
        )
        right_hand_rect = pygame.Rect(
            right_arm_rect.right - DRINK_SCENE_BARTENDER_HAND_SIZE - DRINK_SCENE_BARTENDER_HAND_X_INSET,
            right_arm_rect.bottom - DRINK_SCENE_BARTENDER_HAND_BOTTOM_OFFSET,
            DRINK_SCENE_BARTENDER_HAND_SIZE,
            DRINK_SCENE_BARTENDER_HAND_SIZE,
        )

        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SHIRT_COLOR, body_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SHIRT_COLOR, left_arm_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SHIRT_COLOR, right_arm_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SHIRT_COLOR, left_leg_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SHIRT_COLOR, right_leg_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_APRON_COLOR, apron_rect)
        if self.round_bartender_has_bowtie or self.run_bartender_has_bowtie:
            self._draw_drink_scene_bartender_bowtie(surface, body_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SKIN_COLOR, head_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SKIN_COLOR, left_hand_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SKIN_COLOR, right_hand_rect)
        if self.round_bartender_has_glasses or self.run_bartender_has_glasses:
            self._draw_drink_scene_bartender_glasses(surface, head_rect)
        if self.round_bartender_has_cigar or self.run_bartender_has_cigar:
            self._draw_drink_scene_bartender_cigar(surface, head_rect)

        if self.drink_scene_active_index is not None:
            active_mug_rect, _ = self._drink_scene_slot_geometry(center_x, self.drink_scene_active_index, body_rect)
            self._draw_drink_scene_reach(surface, body_rect, active_mug_rect)

        if self.round_bartender_has_hat or self.run_bartender_has_hat:
            self._draw_drink_scene_bartender_hat(surface, head_rect)

    def _draw_drink_scene_reach(
        self,
        surface: pygame.Surface,
        body_rect: pygame.Rect,
        target_rect: pygame.Rect,
    ) -> None:
        shoulder_x = body_rect.left + DRINK_SCENE_REACH_SHOULDER_X_OFFSET
        shoulder_y = body_rect.top + DRINK_SCENE_REACH_SHOULDER_Y_OFFSET
        pygame.draw.line(
            surface,
            DRINK_SCENE_BARTENDER_SHIRT_COLOR,
            (shoulder_x, shoulder_y),
            self._drink_scene_grab_hand_rect(target_rect).center,
            DRINK_SCENE_BARTENDER_ARM_WIDTH,
        )

    def _draw_drink_scene_grab_hand(self, surface: pygame.Surface, target_rect: pygame.Rect) -> None:
        hand_rect = self._drink_scene_grab_hand_rect(target_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_SKIN_COLOR, hand_rect)

    def _draw_drink_scene_bartender_hat(self, surface: pygame.Surface, head_rect: pygame.Rect) -> None:
        brim_rect = pygame.Rect(
            head_rect.centerx - (DRINK_SCENE_BARTENDER_HAT_WIDTH // 2),
            head_rect.top + DRINK_SCENE_BARTENDER_HAT_Y_OFFSET,
            DRINK_SCENE_BARTENDER_HAT_WIDTH,
            DRINK_SCENE_BARTENDER_HAT_BRIM_HEIGHT,
        )
        crown_rect = pygame.Rect(
            brim_rect.left + DRINK_SCENE_BARTENDER_HAT_CROWN_INSET,
            brim_rect.top - (DRINK_SCENE_BARTENDER_HAT_HEIGHT - DRINK_SCENE_BARTENDER_HAT_BRIM_HEIGHT),
            brim_rect.width - (DRINK_SCENE_BARTENDER_HAT_CROWN_INSET * 2),
            DRINK_SCENE_BARTENDER_HAT_HEIGHT,
        )
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_HAT_COLOR, crown_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_HAT_COLOR, brim_rect)

    def _draw_drink_scene_bartender_bowtie(self, surface: pygame.Surface, body_rect: pygame.Rect) -> None:
        center_x = body_rect.centerx
        center_y = body_rect.top + DRINK_SCENE_BARTENDER_BOWTIE_Y
        left_points = [
            (center_x - 1, center_y),
            (center_x - (DRINK_SCENE_BARTENDER_BOWTIE_WIDTH // 2), center_y - (DRINK_SCENE_BARTENDER_BOWTIE_HEIGHT // 2)),
            (center_x - (DRINK_SCENE_BARTENDER_BOWTIE_WIDTH // 2), center_y + (DRINK_SCENE_BARTENDER_BOWTIE_HEIGHT // 2)),
        ]
        right_points = [
            (center_x + 1, center_y),
            (center_x + (DRINK_SCENE_BARTENDER_BOWTIE_WIDTH // 2), center_y - (DRINK_SCENE_BARTENDER_BOWTIE_HEIGHT // 2)),
            (center_x + (DRINK_SCENE_BARTENDER_BOWTIE_WIDTH // 2), center_y + (DRINK_SCENE_BARTENDER_BOWTIE_HEIGHT // 2)),
        ]
        center_rect = pygame.Rect(
            center_x - (DRINK_SCENE_BARTENDER_BOWTIE_CENTER // 2),
            center_y - (DRINK_SCENE_BARTENDER_BOWTIE_CENTER // 2),
            DRINK_SCENE_BARTENDER_BOWTIE_CENTER,
            DRINK_SCENE_BARTENDER_BOWTIE_CENTER,
        )
        pygame.draw.polygon(surface, DRINK_SCENE_BARTENDER_BOWTIE_COLOR, left_points)
        pygame.draw.polygon(surface, DRINK_SCENE_BARTENDER_BOWTIE_COLOR, right_points)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_BOWTIE_COLOR, center_rect)

    def _draw_drink_scene_bartender_glasses(self, surface: pygame.Surface, head_rect: pygame.Rect) -> None:
        total_bridge_width = DRINK_SCENE_BARTENDER_GLASSES_BRIDGE * 2
        lens_width = (DRINK_SCENE_BARTENDER_GLASSES_WIDTH - total_bridge_width) // 2
        lens_top = head_rect.top + DRINK_SCENE_BARTENDER_GLASSES_Y_OFFSET
        left_lens_rect = pygame.Rect(
            head_rect.centerx - DRINK_SCENE_BARTENDER_GLASSES_BRIDGE - lens_width,
            lens_top,
            lens_width,
            DRINK_SCENE_BARTENDER_GLASSES_HEIGHT,
        )
        right_lens_rect = pygame.Rect(
            head_rect.centerx + DRINK_SCENE_BARTENDER_GLASSES_BRIDGE,
            lens_top,
            lens_width,
            DRINK_SCENE_BARTENDER_GLASSES_HEIGHT,
        )
        bridge_rect = pygame.Rect(
            left_lens_rect.right,
            lens_top + (DRINK_SCENE_BARTENDER_GLASSES_HEIGHT // 2) - 1,
            right_lens_rect.left - left_lens_rect.right,
            2,
        )
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_GLASSES_COLOR, left_lens_rect, 1)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_GLASSES_COLOR, right_lens_rect, 1)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_GLASSES_COLOR, bridge_rect)

    def _draw_drink_scene_bartender_cigar(self, surface: pygame.Surface, head_rect: pygame.Rect) -> None:
        cigar_rect = pygame.Rect(
            head_rect.centerx - DRINK_SCENE_BARTENDER_CIGAR_X_OFFSET - DRINK_SCENE_BARTENDER_CIGAR_WIDTH,
            head_rect.top + DRINK_SCENE_BARTENDER_CIGAR_Y_OFFSET,
            DRINK_SCENE_BARTENDER_CIGAR_WIDTH,
            DRINK_SCENE_BARTENDER_CIGAR_HEIGHT,
        )
        ember_rect = pygame.Rect(
            cigar_rect.left,
            cigar_rect.top,
            2,
            cigar_rect.height,
        )
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_CIGAR_COLOR, cigar_rect)
        pygame.draw.rect(surface, DRINK_SCENE_BARTENDER_CIGAR_EMBER_COLOR, ember_rect)

    def _draw_drink_scene_slots(self, surface: pygame.Surface, center_x: int) -> None:
        if not self.drink_scene_slots:
            return

        beer_fill_color = self._active_beer_fill_color()
        bartender_body_rect = self._drink_scene_bartender_body_rect(center_x)
        for index, slot in enumerate(self.drink_scene_slots):
            mug_center_x = self._drink_scene_slot_center_x(center_x, index)
            is_purchased = index in self.drink_scene_purchased_indices
            mug_rect, fill_ratio = self._drink_scene_slot_geometry(center_x, index, bartender_body_rect)
            if is_purchased:
                fill_ratio = 0.0
            draw_glass_with_fill(
                surface,
                mug_rect,
                fill_ratio=fill_ratio,
                fill_color=beer_fill_color,
                show_top_foam=fill_ratio >= 0.99,
            )

            if is_purchased:
                glow_rect = mug_rect.inflate(DRINK_SCENE_SLOT_PURCHASED_GLOW_INFLATE, DRINK_SCENE_SLOT_PURCHASED_GLOW_INFLATE)
                pygame.draw.rect(
                    surface,
                    DRINK_SCENE_PURCHASED_GLOW_COLOR,
                    glow_rect,
                    DRINK_SCENE_SLOT_PURCHASED_GLOW_WIDTH,
                    border_radius=DRINK_SCENE_SLOT_PURCHASED_GLOW_RADIUS,
                )
            if index == self.drink_scene_selected_index:
                highlight_rect = mug_rect.inflate(
                    DRINK_SCENE_SLOT_SELECTED_HIGHLIGHT_INFLATE,
                    DRINK_SCENE_SLOT_SELECTED_HIGHLIGHT_INFLATE,
                )
                highlight_color = DRINK_SCENE_SELECTED_OUTLINE_COLOR
                if is_purchased:
                    highlight_color = DRINK_SCENE_PURCHASED_GLOW_COLOR
                elif slot.kind == "upgrade" and not self._can_afford_drink_scene_slot(slot):
                    highlight_color = DRINK_SCENE_UNAFFORDABLE_COLOR
                pygame.draw.rect(
                    surface,
                    highlight_color,
                    highlight_rect,
                    DRINK_SCENE_SLOT_SELECTED_HIGHLIGHT_WIDTH,
                    border_radius=DRINK_SCENE_SLOT_SELECTED_HIGHLIGHT_RADIUS,
                )

            if slot.kind == "upgrade" and slot.offer is not None:
                label = self._format_drink_scene_offer_label(slot.offer)
                bonus = ""
                cost = "" if is_purchased else self._format_offer_cash(slot.offer.cost)
                status = self._format_drink_scene_status(index, slot)
            else:
                label = "CONTINUE"
                bonus = ""
                cost = "FREE BEER"
                status = ""

            label_surface = self.drink_scene_detail_font.render(label, True, OVERLAY_TEXT_COLOR)
            surface.blit(label_surface, label_surface.get_rect(center=(mug_center_x, DRINK_SCENE_LABEL_Y)))

            if bonus:
                bonus_color = DRINK_SCENE_CONTINUE_BONUS_COLOR if slot.kind == "continue" else OVERLAY_TEXT_COLOR
                bonus_surface = self.detail_font.render(bonus, True, bonus_color)
                surface.blit(bonus_surface, bonus_surface.get_rect(center=(mug_center_x, DRINK_SCENE_BONUS_Y)))

            if cost:
                cost_surface = self.detail_font.render(cost, True, OVERLAY_TEXT_COLOR)
                surface.blit(cost_surface, cost_surface.get_rect(center=(mug_center_x, DRINK_SCENE_COST_Y)))

            if status:
                status_color = DRINK_SCENE_PURCHASED_GLOW_COLOR if status == DRINK_SCENE_PURCHASED_LABEL else DRINK_SCENE_UNAFFORDABLE_COLOR
                status_surface = self.detail_font.render(status, True, status_color)
                surface.blit(status_surface, status_surface.get_rect(center=(mug_center_x, DRINK_SCENE_STATUS_Y)))

    def _format_drink_scene_offer_label(self, offer: UpgradeOffer) -> str:
        if offer.definition.id == GREEN_BEER_THEME_ID:
            return "GREEN BEER"
        return offer.definition.name.upper()

    def _finish_fail_feedback(self) -> None:
        if self.pending_game_over:
            self.fail_message = None
            self.pending_game_over = False
            self.flow_state = FlowState.GAME_OVER
            return

        self._reset_level_progress()
        self._reset_round()

    def _draw_fail_overlay(self, surface: pygame.Surface) -> None:
        if self.fail_message is None:
            return

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill(FAIL_OVERLAY_COLOR)
        surface.blit(overlay, (0, 0))

        title = self.overlay_font.render(self.fail_message, True, OVERLAY_TEXT_COLOR)
        title_rect = title.get_rect(center=(surface.get_width() // 2, FAIL_MESSAGE_Y))
        surface.blit(title, title_rect)

    def _fail_shake_offset(self) -> tuple[int, int]:
        if self.fail_feedback_timer <= 0.0:
            return (0, 0)

        frame_index = int((FAIL_FEEDBACK_DURATION - self.fail_feedback_timer) * FAIL_SHAKE_FPS)
        return FAIL_SHAKE_PATTERN[frame_index % len(FAIL_SHAKE_PATTERN)]

    def _any_key_pressed(self) -> bool:
        return any(pygame.key.get_pressed())

    def build_upgrade_offer(self, upgrade: UpgradeDefinition) -> UpgradeOffer:
        return UpgradeOffer(
            definition=upgrade,
            level=self.current_level,
            owned_stacks=self.upgrade_stacks.get(upgrade.id, 0),
        )

    def _move_drink_scene_selection(self, direction: int) -> None:
        if not self.drink_scene_slots:
            return
        self.drink_scene_selected_index = (self.drink_scene_selected_index + direction) % len(self.drink_scene_slots)

    def _start_drink_scene_drink(self) -> None:
        if not self.drink_scene_slots:
            return
        if not self._can_activate_drink_scene_slot(self.drink_scene_selected_index):
            return
        self.drink_scene_active_index = self.drink_scene_selected_index
        self.drink_scene_drink_progress = 0.0
        self.drink_scene_space_held = True
        self.drink_scene_hold_timer = 0.0
        self.drink_scene_return_progress = 0.0

    def _clear_drink_scene_drink(self) -> None:
        self.drink_scene_active_index = None
        self.drink_scene_drink_progress = 0.0
        self.drink_scene_space_held = False
        self.drink_scene_hold_timer = 0.0
        self.drink_scene_return_progress = 0.0

    def _pause_drink_scene_drink(self) -> None:
        if not self._is_drink_scene_drinking():
            return
        self.drink_scene_space_held = False

    def _is_drink_scene_drinking(self) -> bool:
        return self.drink_scene_active_index is not None

    def _update_drink_scene_drink(self, dt: float) -> None:
        if self.drink_scene_active_index is None:
            return
        if self.drink_scene_drink_progress >= 1.0:
            if self.drink_scene_hold_timer > 0.0:
                self.drink_scene_hold_timer = max(0.0, self.drink_scene_hold_timer - dt)
                return
            self.drink_scene_return_progress = min(
                1.0,
                self.drink_scene_return_progress + (dt / DRINK_SCENE_DRINK_RETURN_DURATION),
            )
            if self.drink_scene_return_progress >= 1.0:
                self._complete_drink_scene_choice()
            return

        if not self.drink_scene_space_held:
            return

        self.drink_scene_drink_progress = min(
            1.0,
            self.drink_scene_drink_progress + (self._effective_tap_fill_rate() * dt),
        )
        if self.drink_scene_drink_progress >= 1.0:
            self.drink_scene_space_held = False
            self.drink_scene_hold_timer = DRINK_SCENE_DRINK_HOLD_DURATION
            self.drink_scene_return_progress = 0.0

    def _complete_drink_scene_choice(self) -> None:
        if self.drink_scene_active_index is None or not self.drink_scene_slots:
            return

        selected_index = self.drink_scene_active_index
        selected_slot = self.drink_scene_slots[selected_index]
        self._clear_drink_scene_drink()

        if selected_slot.kind == "continue":
            self._advance_to_next_round()
            return

        offer = selected_slot.offer
        if offer is None or not self._can_activate_drink_scene_slot(selected_index):
            return

        self.cash -= offer.cost
        self._apply_upgrade_offer(offer)
        self.drink_scene_purchased_indices.add(selected_index)

    def _apply_upgrade_offer(self, offer: UpgradeOffer) -> None:
        upgrade_id = offer.definition.id

        effect_type = offer.definition.effect_type
        bonus = offer.bonus
        if effect_type == GREEN_BEER_THEME_ID:
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.pending_next_round_beer_theme = GREEN_BEER_THEME_ID
        elif effect_type == WINE_BEER_THEME_ID:
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.pending_next_round_beer_theme = WINE_BEER_THEME_ID
        elif effect_type == HAT_COSMETIC_ID:
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.run_bartender_has_hat = True
        elif effect_type == BOWTIE_COSMETIC_ID:
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.run_bartender_has_bowtie = True
        elif effect_type == GLASSES_COSMETIC_ID:
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.run_bartender_has_glasses = True
        elif effect_type == CIGAR_COSMETIC_ID:
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.run_bartender_has_cigar = True
        elif effect_type == "quick_pour":
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.run_modifiers.quick_pour_fill_duration_delta += TAP_FILL_DURATION * bonus
        elif effect_type == "fast_serve":
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.run_modifiers.fast_serve_speed_bonus += FLYING_GLASS_SPEED * bonus
        elif effect_type == "quick_feet":
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.run_modifiers.quick_feet_speed_bonus += BARTENDER_WALK_SPEED * bonus
        elif effect_type == "long_reach":
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.run_modifiers.long_reach_padding_bonus += max(
                1,
                int(round(BARTENDER_CATCH_RECT_PADDING[0] * bonus)),
            )
        elif effect_type == "last_call":
            self.upgrade_stacks[upgrade_id] = self.upgrade_stacks.get(upgrade_id, 0) + 1
            self.lives += 1
        elif effect_type == "lucky_tips":
            self.pending_next_round_lucky_tips_chance_bonus += bonus
        elif effect_type == "bigger_tips":
            self.pending_next_round_bigger_tips_cash_bonus += bonus

    def _activate_pending_round_beer_theme(self) -> None:
        self.active_round_beer_theme = self.pending_next_round_beer_theme
        self.pending_next_round_beer_theme = None

    def _clear_active_round_beer_theme(self) -> None:
        self.active_round_beer_theme = None

    def _activate_pending_round_tip_modifiers(self) -> None:
        self.active_round_lucky_tips_chance_bonus = self.pending_next_round_lucky_tips_chance_bonus
        self.active_round_bigger_tips_cash_bonus = self.pending_next_round_bigger_tips_cash_bonus
        self.pending_next_round_lucky_tips_chance_bonus = 0.0
        self.pending_next_round_bigger_tips_cash_bonus = 0.0

    def _clear_active_round_tip_modifiers(self) -> None:
        self.active_round_lucky_tips_chance_bonus = 0.0
        self.active_round_bigger_tips_cash_bonus = 0.0

    def _apply_round_cosmetic_state(self) -> None:
        self.round_bartender_has_hat = self.run_bartender_has_hat
        self.round_bartender_has_bowtie = self.run_bartender_has_bowtie
        self.round_bartender_has_glasses = self.run_bartender_has_glasses
        self.round_bartender_has_cigar = self.run_bartender_has_cigar
        if self.first_round_cosmetic_test_pending:
            self.round_bartender_has_hat = True
            self.round_bartender_has_bowtie = True
            self.round_bartender_has_glasses = True
            self.round_bartender_has_cigar = True
            self.active_round_beer_theme = GREEN_BEER_THEME_ID
            self.first_round_cosmetic_test_pending = False

    def _build_drink_scene_slots(self) -> list[DrinkSceneSlot]:
        return [
            DrinkSceneSlot(kind="upgrade", offer=offer)
            for offer in self._choose_shop_offers(2)
        ] + [DrinkSceneSlot(kind="continue")]

    def _choose_shop_offers(self, count: int) -> list[UpgradeOffer]:
        available_offers = [
            self.build_upgrade_offer(upgrade)
            for upgrade in self.upgrade_definitions
            if self.build_upgrade_offer(upgrade).can_offer
        ]
        chosen_offers: list[UpgradeOffer] = []
        remaining_offers = list(available_offers)
        picks = min(count, len(remaining_offers))
        for _ in range(picks):
            total_weight = sum(self._shop_offer_weight(offer) for offer in remaining_offers)
            roll = self.patron_rng.uniform(0.0, float(total_weight))
            running_weight = 0.0
            selected_index = 0
            for index, offer in enumerate(remaining_offers):
                running_weight += self._shop_offer_weight(offer)
                if roll <= running_weight:
                    selected_index = index
                    break
            chosen_offers.append(remaining_offers.pop(selected_index))
        return chosen_offers

    def _shop_offer_weight(self, offer: UpgradeOffer) -> float:
        weight = float(offer.definition.weight)
        weight *= self._shop_cost_band_weight_multiplier(offer.cost)
        weight *= self._contextual_weight_multiplier(offer)
        if offer.definition.is_cosmetic:
            weight *= self._shop_cosmetic_weight_multiplier()

        if offer.cost <= self.cash:
            weight *= AFFORDABLE_OFFER_WEIGHT_MULTIPLIER
        elif offer.cost <= self.cash + NEAR_AFFORDABLE_COST_MARGIN:
            weight *= NEAR_AFFORDABLE_OFFER_WEIGHT_MULTIPLIER

        return max(0.01, weight)

    def _contextual_weight_multiplier(self, offer: UpgradeOffer) -> float:
        multiplier = 1.0
        upgrade = offer.definition

        if upgrade.id == LAST_CALL_UPGRADE.id:
            if self.lives == 1:
                multiplier *= LOW_LIFE_LAST_CALL_WEIGHT_MULTIPLIER
            elif self.lives == 2:
                multiplier *= MID_LIFE_LAST_CALL_WEIGHT_MULTIPLIER

        if not upgrade.is_cosmetic and self._total_owned_upgrades(GAMEPLAY_UPGRADE_DEFINITIONS) == 0:
            multiplier *= NO_GAMEPLAY_UPGRADES_WEIGHT_MULTIPLIER

        if upgrade.is_cosmetic and self._total_owned_upgrades(COSMETIC_UPGRADE_DEFINITIONS) == 0:
            multiplier *= NO_COSMETICS_WEIGHT_MULTIPLIER

        if self.cash > HIGH_CASH_THRESHOLD and offer.cost >= HIGH_CASH_EXPENSIVE_COST_MIN:
            multiplier *= HIGH_CASH_EXPENSIVE_WEIGHT_MULTIPLIER

        if self.cash < LOW_CASH_THRESHOLD and offer.cost <= LOW_CASH_CHEAP_COST_MAX:
            multiplier *= LOW_CASH_CHEAP_WEIGHT_MULTIPLIER

        return multiplier

    def _total_owned_upgrades(self, definitions: tuple[UpgradeDefinition, ...]) -> int:
        return sum(self.upgrade_stacks.get(upgrade.id, 0) for upgrade in definitions)

    def _shop_cosmetic_weight_multiplier(self) -> float:
        if self.current_level <= EARLY_SHOP_LEVEL_MAX:
            return EARLY_COSMETIC_OFFER_WEIGHT_MULTIPLIER
        if self.current_level <= MID_SHOP_LEVEL_MAX:
            return MID_COSMETIC_OFFER_WEIGHT_MULTIPLIER
        return LATE_COSMETIC_OFFER_WEIGHT_MULTIPLIER

    def _shop_cost_band_weight_multiplier(self, cost: int) -> float:
        if self.current_level <= EARLY_SHOP_LEVEL_MAX:
            if cost <= CHEAP_UPGRADE_COST_MAX:
                return EARLY_CHEAP_OFFER_WEIGHT_MULTIPLIER
            if cost <= MID_UPGRADE_COST_MAX:
                return EARLY_MID_OFFER_WEIGHT_MULTIPLIER
            return EARLY_EXPENSIVE_OFFER_WEIGHT_MULTIPLIER

        if self.current_level <= MID_SHOP_LEVEL_MAX:
            if cost <= CHEAP_UPGRADE_COST_MAX:
                return MID_CHEAP_OFFER_WEIGHT_MULTIPLIER
            if cost <= MID_UPGRADE_COST_MAX:
                return MID_MID_OFFER_WEIGHT_MULTIPLIER
            return MID_EXPENSIVE_OFFER_WEIGHT_MULTIPLIER

        if cost <= CHEAP_UPGRADE_COST_MAX:
            return LATE_CHEAP_OFFER_WEIGHT_MULTIPLIER
        if cost <= MID_UPGRADE_COST_MAX:
            return LATE_MID_OFFER_WEIGHT_MULTIPLIER
        return LATE_EXPENSIVE_OFFER_WEIGHT_MULTIPLIER

    def _apply_run_modifiers_to_bartender(self) -> None:
        self.bartender.walk_speed = self._effective_bartender_walk_speed()
        self.bartender.tap_glass.fill_rate = self._effective_tap_fill_rate()
        self.bartender.flying_glass_speed = self._effective_flying_glass_speed()
        self.bartender.catch_rect_padding = self._effective_catch_rect_padding()
        self.bartender.has_hat = self.round_bartender_has_hat
        self.bartender.has_bowtie = self.round_bartender_has_bowtie
        self.bartender.has_glasses = self.round_bartender_has_glasses
        self.bartender.has_cigar = self.round_bartender_has_cigar

    def _effective_bartender_walk_speed(self) -> float:
        return BARTENDER_WALK_SPEED + self.run_modifiers.quick_feet_speed_bonus

    def _effective_tap_fill_duration(self) -> float:
        return max(0.05, TAP_FILL_DURATION - self.run_modifiers.quick_pour_fill_duration_delta)

    def _effective_tap_fill_rate(self) -> float:
        return 1.0 / self._effective_tap_fill_duration()

    def _effective_flying_glass_speed(self) -> float:
        return FLYING_GLASS_SPEED + self.run_modifiers.fast_serve_speed_bonus

    def _effective_catch_rect_padding(self) -> tuple[int, int]:
        horizontal = BARTENDER_CATCH_RECT_PADDING[0] + self.run_modifiers.long_reach_padding_bonus
        vertical = BARTENDER_CATCH_RECT_PADDING[1] + max(
            0,
            self.run_modifiers.long_reach_padding_bonus // 2,
        )
        return (horizontal, vertical)

    def _effective_tip_chance(self, patron: Patron) -> float:
        return min(1.0, (patron.tip_chance * TIP_SPAWN_RATE_MULTIPLIER) + self.active_round_lucky_tips_chance_bonus)

    def _effective_tip_cash_reward(self) -> float:
        return TIP_CASH + self.active_round_bigger_tips_cash_bonus

    def _active_beer_fill_color(self) -> pygame.Color | None:
        if self.active_round_beer_theme == GREEN_BEER_THEME_ID:
            return GREEN_BEER_FILL_COLOR
        if self.active_round_beer_theme == WINE_BEER_THEME_ID:
            return WINE_BEER_FILL_COLOR
        return None

    def _can_afford_drink_scene_slot(self, slot: DrinkSceneSlot) -> bool:
        if slot.kind != "upgrade":
            return True
        return slot.offer is not None and self.cash >= slot.offer.cost

    def _can_activate_drink_scene_slot(self, index: int) -> bool:
        if not (0 <= index < len(self.drink_scene_slots)):
            return False
        if index in self.drink_scene_purchased_indices:
            return False
        return self._can_afford_drink_scene_slot(self.drink_scene_slots[index])

    def _format_drink_scene_status(self, index: int, slot: DrinkSceneSlot) -> str:
        if index in self.drink_scene_purchased_indices:
            return DRINK_SCENE_PURCHASED_LABEL
        if slot.kind != "upgrade" or slot.offer is None or self._can_afford_drink_scene_slot(slot):
            return ""
        return self._format_cash_shortfall(slot.offer.cost - self.cash)
