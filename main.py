from __future__ import annotations

import asyncio

import pygame

from game import Game
from renderer import FPS, LOGICAL_HEIGHT, LOGICAL_WIDTH, WINDOW_HEIGHT, WINDOW_WIDTH


async def main() -> None:
    pygame.init()
    pygame.display.set_caption("Tapper")

    window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
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
                game.handle_event(event)

            if not running:
                continue

            game.update(dt)
            game.draw(logical_surface)
            scaled_surface = pygame.transform.scale(
                logical_surface,
                (WINDOW_WIDTH, WINDOW_HEIGHT),
            )
            window.blit(scaled_surface, (0, 0))
            pygame.display.flip()
            await asyncio.sleep(0)
    finally:
        pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
