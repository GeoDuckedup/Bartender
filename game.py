from __future__ import annotations

from dataclasses import dataclass
from random import Random

import pygame

from bartender import Bartender
from glass import ReturningGlass
from hud import HUDRenderer
from patron import PATRON_ARCHETYPES, Patron, build_walk_speed_rng
from renderer import BAR_COUNT, SceneRenderer
from tip import Tip


@dataclass(frozen=True)
class LevelConfig:
    target_serves: int
    spawn_interval: float
    min_walk_speed: float
    max_walk_speed: float
    long_shove_weight: float
    offscreen_shove_weight: float
    short_shove_weight: float


def build_level_config(level_number: int) -> LevelConfig:
    level = max(1, level_number)
    if level == 1:
        shove_weights = (0.60, 0.25, 0.15)
    elif level == 2:
        shove_weights = (0.55, 0.30, 0.15)
    else:
        shove_weights = (0.50, 0.35, 0.15)

    return LevelConfig(
        target_serves=10 + ((level - 1) * 5),
        spawn_interval=max(0.75, 3.0 - ((level - 1) * 0.18)),
        min_walk_speed=16.0 + ((level - 1) * 2.0),
        max_walk_speed=24.0 + ((level - 1) * 3.0),
        long_shove_weight=shove_weights[0],
        offscreen_shove_weight=shove_weights[1],
        short_shove_weight=shove_weights[2],
    )


class Game:
    MAX_PATRONS_PER_LANE = 3
    SPAWN_X = -Patron.BODY_WIDTH
    STARTING_LIVES = 3
    MAX_LIVES = 99
    INITIAL_SPAWN_DELAY = 0.35
    FAIL_FEEDBACK_DURATION = 0.6
    FAIL_SHAKE_AMPLITUDE = 4
    BEER_SERVED_SCORE = 10
    TIP_SCORE = 25
    LIVES_REMAINING_BONUS = 100
    TIP_SPAWN_CHANCE = 0.35
    MIN_DRINK_DURATION = 0.95
    MAX_DRINK_DURATION = 1.45

    def __init__(self) -> None:
        self.scene_renderer = SceneRenderer()
        self.hud_renderer = HUDRenderer()
        self.overlay_font = pygame.font.SysFont("couriernew", 18, bold=True)
        self.detail_font = pygame.font.SysFont("couriernew", 12, bold=True)
        self._reset_game()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.fail_feedback_timer > 0.0:
            return

        if self.game_over:
            if event.type == pygame.KEYDOWN:
                self._reset_game()
            return

        if self.level_cleared:
            if self.awaiting_level_clear_release:
                return
            if event.type == pygame.KEYDOWN:
                self._advance_to_next_round()
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
        )
        if is_arrow and self.bartender.is_pouring:
            self.bartender.cancel_pour()

        if event.key == pygame.K_UP:
            self.bartender.move_up()
        elif event.key == pygame.K_DOWN:
            self.bartender.move_down()

    def update(self, dt: float) -> None:
        if self.fail_feedback_timer > 0.0:
            self.fail_feedback_timer = max(0.0, self.fail_feedback_timer - dt)
            if self.fail_feedback_timer == 0.0:
                self._finish_fail_feedback()
            return

        if self.level_cleared:
            if self.awaiting_level_clear_release and not self._any_key_pressed():
                self.awaiting_level_clear_release = False
            return

        if self.game_over:
            return

        if not self.bartender.is_pouring:
            pressed = pygame.key.get_pressed()
            if pressed[pygame.K_LEFT] and not pressed[pygame.K_RIGHT]:
                self.bartender.walk_left(dt)
            elif pressed[pygame.K_RIGHT] and not pressed[pygame.K_LEFT]:
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
        if self.level_cleared:
            return

    def draw(self, surface: pygame.Surface) -> None:
        if self.fail_feedback_timer > 0.0:
            frame_surface = pygame.Surface(surface.get_size())
            self._draw_frame(frame_surface)
            shake_x, shake_y = self._fail_shake_offset()
            surface.fill((0, 0, 0))
            surface.blit(frame_surface, (shake_x, shake_y))
            self._draw_fail_overlay(surface)
            return

        self._draw_frame(surface)

    def _draw_frame(self, surface: pygame.Surface) -> None:
        self.scene_renderer.draw_scene_backdrop(surface)
        for patron in reversed(self.patrons):
            patron.draw(surface)
        self.scene_renderer.draw_bar_fronts(surface)
        for patron in reversed(self.patrons):
            patron.draw_held_glass(surface)
        for tip in self.tips:
            tip.draw(surface)
        for returning_glass in self.returning_glasses:
            returning_glass.draw(surface)
        self.bartender.draw_flying_glasses(surface)
        self.bartender.draw(surface)
        self.bartender.draw_tap_glass(surface)
        self.bartender.draw_serve_visual(surface)
        self.hud_renderer.draw(
            surface,
            lives=self.lives,
            current_level=self.current_level,
            served=self.served_count,
            target=self.level_config.target_serves,
            score=self.score,
        )
        if self.level_cleared:
            self._draw_level_clear_overlay(surface)
        if self.game_over:
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
                self._maybe_spawn_tip(frontmost_patron)
                frontmost_patron.receive_beer(flying_glass.fill_ratio)
                self.score += self.BEER_SERVED_SCORE
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

            walking_patrons = sorted(
                (patron for patron in lane_patrons if patron.can_receive_beer),
                key=lambda patron: patron.x,
                reverse=True,
            )
            leader: Patron | None = None
            for patron in walking_patrons:
                max_walk_x = None
                if leader is not None:
                    max_walk_x = leader.x - Patron.BODY_WIDTH - Patron.QUEUE_GAP
                patron.update(dt, max_walk_x=max_walk_x)
                leader = patron

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
            if len(lane_patrons) >= self.MAX_PATRONS_PER_LANE:
                continue
            if not self._lane_has_spawn_room(lane_patrons):
                continue

            archetype = self.patron_rng.choice(PATRON_ARCHETYPES)
            base_walk_speed = self.patron_rng.uniform(
                self.level_config.min_walk_speed,
                self.level_config.max_walk_speed,
            )
            base_drink_duration = self.patron_rng.uniform(
                self.MIN_DRINK_DURATION,
                self.MAX_DRINK_DURATION,
            )
            self.patrons.append(
                Patron(
                    bar_index=bar_index,
                    start_x=float(self.SPAWN_X),
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

        spawn_clear_x = self.SPAWN_X + Patron.BODY_WIDTH + Patron.QUEUE_GAP
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

    def _maybe_spawn_tip(self, patron: Patron) -> None:
        if self.tip_rng.random() > patron.tip_chance:
            return
        tip_x = float(patron.body_rect.centerx - (Tip.WIDTH / 2))
        self.tips.append(Tip(x=tip_x, bar_index=patron.bar_index))

    def _collect_tips(self) -> None:
        active_tips: list[Tip] = []
        for tip in self.tips:
            if (
                tip.bar_index == self.bartender.bar_index
                and tip.rect.colliderect(self.bartender.body_rect)
            ):
                self.score += self.TIP_SCORE
                self.tip_score += self.TIP_SCORE
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
        self.lives = max(0, self.lives - 1)
        self.fail_message = fail_reason
        self.fail_feedback_timer = self.FAIL_FEEDBACK_DURATION
        self.pending_game_over = self.lives == 0

    def _reset_round(self) -> None:
        self.bartender = Bartender()
        self.patrons = []
        self.tips = []
        self.returning_glasses = []
        self.missed_return_glass = False
        self.spawn_timer = max(0.0, self.level_config.spawn_interval - self.INITIAL_SPAWN_DELAY)
        self.next_spawn_bar = self.patron_rng.randrange(BAR_COUNT)
        self.fail_feedback_timer = 0.0
        self.fail_message = None
        self.pending_game_over = False

    def _reset_game(self) -> None:
        self.current_level = 1
        self.level_config = build_level_config(self.current_level)
        self.lives = self.STARTING_LIVES
        self.score = 0
        self.game_over = False
        self.level_cleared = False
        self.level_clear_summary: dict[str, int] | None = None
        self.awaiting_level_clear_release = False
        self.patron_rng = build_walk_speed_rng()
        self.tip_rng = Random(1984)
        self._reset_level_progress()
        self._reset_round()

    def _advance_to_next_round(self) -> None:
        self.lives = min(self.MAX_LIVES, self.lives + 1)
        self.current_level += 1
        self.level_config = build_level_config(self.current_level)
        self.level_cleared = False
        self.level_clear_summary = None
        self.awaiting_level_clear_release = False
        self._reset_level_progress()
        self._reset_round()

    def _reset_level_progress(self) -> None:
        self.served_count = 0
        self.tips_collected = 0
        self.tip_score = 0

    def _enter_level_clear(self) -> None:
        if self.level_cleared:
            return

        beer_score = self.served_count * self.BEER_SERVED_SCORE
        tips_score = self.tip_score
        lives_bonus = self.lives * self.LIVES_REMAINING_BONUS
        self.score += lives_bonus
        self.level_cleared = True
        self.awaiting_level_clear_release = True
        self.level_clear_summary = {
            "level": self.current_level,
            "beer_score": beer_score,
            "tips_score": tips_score,
            "lives_bonus": lives_bonus,
            "total_score": self.score,
        }

    def _draw_game_over_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        title = self.overlay_font.render("GAME OVER", True, pygame.Color("#F5F0E8"))
        prompt = self.detail_font.render(
            "PRESS ANY KEY TO RESTART",
            True,
            pygame.Color("#F5F0E8"),
        )

        title_rect = title.get_rect(center=(surface.get_width() // 2, 138))
        prompt_rect = prompt.get_rect(center=(surface.get_width() // 2, 160))
        surface.blit(title, title_rect)
        surface.blit(prompt, prompt_rect)

    def _draw_level_clear_overlay(self, surface: pygame.Surface) -> None:
        summary = self.level_clear_summary
        if summary is None:
            return

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surface.blit(overlay, (0, 0))

        title = self.overlay_font.render(
            f"LEVEL {summary['level']:02d} CLEAR",
            True,
            pygame.Color("#F5F0E8"),
        )
        prompt = self.detail_font.render(
            f"PRESS ANY KEY FOR LEVEL {self.current_level + 1:02d}",
            True,
            pygame.Color("#F5F0E8"),
        )
        beer_line = self.detail_font.render(
            f"BEER SCORE   {summary['beer_score']:04d}",
            True,
            pygame.Color("#F5F0E8"),
        )
        tips_line = self.detail_font.render(
            f"TIPS         {summary['tips_score']:04d}",
            True,
            pygame.Color("#F5F0E8"),
        )
        lives_line = self.detail_font.render(
            f"LIVES BONUS  {summary['lives_bonus']:04d}",
            True,
            pygame.Color("#F5F0E8"),
        )
        total_line = self.detail_font.render(
            f"TOTAL SCORE  {summary['total_score']:06d}",
            True,
            pygame.Color("#F5F0E8"),
        )

        center_x = surface.get_width() // 2
        surface.blit(title, title.get_rect(center=(center_x, 118)))
        surface.blit(beer_line, beer_line.get_rect(center=(center_x, 146)))
        surface.blit(tips_line, tips_line.get_rect(center=(center_x, 162)))
        surface.blit(lives_line, lives_line.get_rect(center=(center_x, 178)))
        surface.blit(total_line, total_line.get_rect(center=(center_x, 198)))
        surface.blit(prompt, prompt.get_rect(center=(center_x, 224)))

    def _finish_fail_feedback(self) -> None:
        if self.pending_game_over:
            self.fail_message = None
            self.pending_game_over = False
            self.game_over = True
            return

        self._reset_level_progress()
        self._reset_round()

    def _draw_fail_overlay(self, surface: pygame.Surface) -> None:
        if self.fail_message is None:
            return

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((32, 0, 0, 80))
        surface.blit(overlay, (0, 0))

        title = self.overlay_font.render(self.fail_message, True, pygame.Color("#F5F0E8"))
        title_rect = title.get_rect(center=(surface.get_width() // 2, 156))
        surface.blit(title, title_rect)

    def _fail_shake_offset(self) -> tuple[int, int]:
        if self.fail_feedback_timer <= 0.0:
            return (0, 0)

        shake_pattern = (
            (0, 0),
            (self.FAIL_SHAKE_AMPLITUDE, -2),
            (-self.FAIL_SHAKE_AMPLITUDE, 2),
            (2, -1),
            (-2, 1),
        )
        frame_index = int((self.FAIL_FEEDBACK_DURATION - self.fail_feedback_timer) * 30)
        return shake_pattern[frame_index % len(shake_pattern)]

    def _any_key_pressed(self) -> bool:
        return any(pygame.key.get_pressed())
