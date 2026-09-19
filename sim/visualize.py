"""Pygame visualization for the warehouse simulation."""

from __future__ import annotations

from .environment import Environment


class Visualizer:
    COLORS = {
        Environment.FREE: (239, 242, 247),
        Environment.OBSTACLE: (55, 65, 81),
        Environment.PICKUP: (34, 197, 94),
        Environment.DROPOFF: (249, 115, 22),
    }
    ROBOT_COLORS = [
        (37, 99, 235),
        (220, 38, 38),
        (147, 51, 234),
        (8, 145, 178),
        (219, 39, 119),
    ]

    def __init__(self, env: Environment, cell_size: int = 28) -> None:
        try:
            import pygame
        except ImportError as exc:
            raise RuntimeError(
                "Pygame is required for visualization; use --headless or install pygame"
            ) from exc
        self.pygame = pygame
        self.env = env
        self.cell_size = cell_size
        pygame.init()
        self.screen = pygame.display.set_mode(
            (env.width * cell_size, env.height * cell_size)
        )
        pygame.display.set_caption("Decentralized AMR Fleet")
        self.font = pygame.font.Font(None, max(14, cell_size // 2))

    def process_events(self) -> bool:
        return not any(
            event.type == self.pygame.QUIT for event in self.pygame.event.get()
        )

    def draw(self) -> None:
        pg = self.pygame
        size = self.cell_size
        for y in range(self.env.height):
            for x in range(self.env.width):
                rect = pg.Rect(x * size, y * size, size, size)
                pg.draw.rect(self.screen, self.COLORS[int(self.env.grid[y, x])], rect)
                pg.draw.rect(self.screen, (203, 213, 225), rect, 1)

        for index, robot in enumerate(self.env.robots.values()):
            color = self.ROBOT_COLORS[index % len(self.ROBOT_COLORS)]
            for x, y in robot.path:
                center = (x * size + size // 2, y * size + size // 2)
                pg.draw.circle(self.screen, color, center, max(2, size // 8))
            x, y = robot.pos
            center = (x * size + size // 2, y * size + size // 2)
            pg.draw.circle(self.screen, color, center, size // 3)
            label = self.font.render(robot.id.split("-")[-1], True, (255, 255, 255))
            self.screen.blit(label, label.get_rect(center=center))
            bar = pg.Rect(x * size + 2, y * size + size - 5, size - 4, 3)
            pg.draw.rect(self.screen, (127, 29, 29), bar)
            pg.draw.rect(
                self.screen,
                (74, 222, 128),
                pg.Rect(bar.x, bar.y, round(bar.width * robot.battery / 100), bar.height),
            )

        # Task endpoints receive an outline so multiple tasks remain readable.
        for task in self.env.tasks:
            for cell, color in ((task.pickup, (21, 128, 61)), (task.dropoff, (194, 65, 12))):
                x, y = cell
                pg.draw.rect(
                    self.screen,
                    color,
                    pg.Rect(x * size + 3, y * size + 3, size - 6, size - 6),
                    2,
                )
        pg.display.flip()

    def save(self, path: str) -> None:
        self.pygame.image.save(self.screen, path)

    def close(self) -> None:
        self.pygame.quit()
