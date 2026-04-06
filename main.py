from __future__ import annotations

import asyncio

import pygame

from game import Game
from renderer import FPS, LOGICAL_HEIGHT, LOGICAL_WIDTH, WINDOW_HEIGHT, WINDOW_WIDTH


async def main() -> None:
    pygame.init()
    pygame.display.set_caption("Tapper")

    fullscreen = False
    window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    logical_surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
    clock = pygame.time.Clock()
    game = Game()

    running = True
    try:
        while running:
            dt = clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    break
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_F11, pygame.K_f):
                    fullscreen = not fullscreen
                    if fullscreen:
                        window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        window = pygame.display.set_mode(
                            (WINDOW_WIDTH, WINDOW_HEIGHT),
                            pygame.RESIZABLE,
                        )
                    continue
                game.handle_event(event)

            if not running:
                continue

            game.update(dt)
            game.draw(logical_surface)
            window_width, window_height = window.get_size()
            scale = min(
                window_width / LOGICAL_WIDTH,
                window_height / LOGICAL_HEIGHT,
            )
            scaled_width = max(1, int(LOGICAL_WIDTH * scale))
            scaled_height = max(1, int(LOGICAL_HEIGHT * scale))
            scaled_surface = pygame.transform.scale(
                logical_surface,
                (scaled_width, scaled_height),
            )
            scaled_rect = scaled_surface.get_rect(
                center=(window_width // 2, window_height // 2),
            )
            window.fill("black")
            window.blit(scaled_surface, scaled_rect)
            pygame.display.flip()
            await asyncio.sleep(0)
    finally:
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
