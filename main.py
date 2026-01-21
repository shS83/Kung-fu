import random
import sys
from typing import List, Tuple

import pygame


def matrix_rain(
    width: int = 960,
    height: int = 540,
    fps: int = 160,
    font_name: str | None = None,
    base_font_size: int = 18,
    fullscreen: bool = False,
    chars: str | None = None,
) -> None:
    """
    Run a Matrix rain (digital rain) visual using Pygame.

    Controls:
    - ESC or Q: quit
    - SPACE: pause/resume
    - UP/DOWN: increase/decrease density
    - LEFT/RIGHT: slow down / speed up
    - R: randomize colors
    - F: toggle fullscreen
    """

    pygame.init()
    flags = pygame.SCALED | pygame.RESIZABLE
    if fullscreen:
        flags |= pygame.FULLSCREEN

    screen = pygame.display.set_mode((width, height), flags)
    pygame.display.set_caption("Matrix Rain")
    
    # Ensure transparency works correctly on some systems
    screen.set_alpha(None)
    clock = pygame.time.Clock()

    # Character set: Katakana + ASCII letters/digits unless custom provided
    if chars is None:
        katakana = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヰヱヲン"
        ascii_set = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz"
        chars = katakana + ascii_set

    # Colors
    def random_green(mode=2) -> Tuple[int, int, int]:
        if mode == 1:
            r = random.randint(100, 255)
            b = 0
            g = 0
            return (r, g, b)
        elif mode == 2:
            r = 0
            b = random.randint(100, 255)
            g = 0
            return (r, g, b)

        if random.random() > 0.3:
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            r = random.randint(0, 255)
        else:
            r = 0
            b = 0
            g = random.randint(100, 255)
        return (r, g, b)

    head_color = (180, 255, 180)
    trail_color = random_green()

    # Prepare font. Monospace preferred if available.
    preferred_fonts = [
        font_name,
        # "ms mincho",
        # "ms gothic",
        # "vl gothic",
        "vl pgothic",
    ]
    font = None
    for f in preferred_fonts:
        if not f:
            continue
        try:
            font = pygame.font.SysFont(f, base_font_size, bold=True)
            if font:
                break
        except Exception:
            pass
    if font is None:
        font = pygame.font.Font(None, base_font_size)

    # Render cache for characters at given size and colors to speed up
    render_cache: dict[Tuple[str, Tuple[int, int, int]], pygame.Surface] = {}

    def render_char(ch: str, color: Tuple[int, int, int]) -> pygame.Surface:
        key = (ch, color)
        surf = render_cache.get(key)
        if surf is None:
            surf = font.render(ch, True, color)
            render_cache[key] = surf
        return surf

    # Calculate grid based on glyph size
    sample = render_char("A", head_color)
    cell_w, cell_h = sample.get_size()

    def recalc_grid(surface_size: Tuple[int, int]):
        w, h = surface_size
        cols = max(1, w // cell_w)
        rows = max(1, h // cell_h)
        return cols, rows

    icon = pygame.Surface((64, 64))
    icon = render_char("A", head_color)
    pygame.display.set_icon(icon)

    cols, rows = recalc_grid(screen.get_size())

    # Create state for each column
    class Column:
        __slots__ = ("y", "speed", "length", "chars")

        def __init__(self):
            self.reset()

        def reset(self):
            self.y = random.randint(-rows, 0)  # start above the screen
            self.speed = random.uniform(8.0, 20.0)  # cells per second
            if not rows:
                self.length = random.randint(100, 5000) // 8
            else:
                self.length = random.randint(rows // 6, rows // 4)
            self.chars = [random.choice(chars) for _ in range(self.length)]

        def step(self, dt: float):
            self.y += self.speed * dt
            # Once the tail is far below the screen, reset
            if self.y - self.length > rows + 2:
                self.reset()
            # Randomly mutate characters for twinkling effect
            if random.random() < 0.3:
                idx = random.randrange(self.length)
                self.chars[idx] = random.choice(chars)

    # We create enough columns for up to 2.0 density
    columns: List[Column] = [Column() for _ in range(cols * 2)]

    # Trail surface with alpha fade to create motion blur effect
    trail = pygame.Surface(screen.get_size(), pygame.SRCALPHA).convert_alpha()
    fade_strength = 50  # larger = faster fading

    paused = False
    density = 1.4  # multiplier for number of columns drawn
    speed_scale = 2.5

    running = True
    while running:
        trail_color = random_green()
        dt = clock.tick(fps) / 6000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_UP:
                    density = min(2.0, density + 0.1)
                elif event.key == pygame.K_DOWN:
                    density = max(0.2, density - 0.1)
                elif event.key == pygame.K_RIGHT:
                    speed_scale = min(3.0, speed_scale + 0.1)
                elif event.key == pygame.K_LEFT:
                    speed_scale = max(0.2, speed_scale - 0.1)
                elif event.key == pygame.K_r:
                    head_color = (180, 255, 180)
                    trail_color = random_green()
                    render_cache.clear()
                elif event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
            elif event.type == pygame.VIDEORESIZE:
                # Recreate screen and trail surface on resize
                cols, rows = recalc_grid(event.size)
                columns = [Column() for _ in range(cols * 2)]
                trail = pygame.Surface(event.size, pygame.SRCALPHA).convert_alpha()

        if paused:
            pygame.display.flip()
            continue

        # Slightly fade the trail surface by drawing a translucent black rect
        trail.fill((0, 0, 0, fade_strength), special_flags=pygame.BLEND_RGBA_SUB)

        screen.fill((0, 0, 0))

        # Draw columns onto the trail surface
        active_cols_count = int(cols * density)
        for ci in range(active_cols_count):
            # Use modulo to wrap around if density > 1.0, 
            # ensuring we have enough variety from the doubled columns list.
            col = columns[ci % len(columns)]
            col.step(dt * speed_scale)

            # draw each glyph in the column
            head_index = int(col.y)
            for i in range(col.length):
                ry = head_index - i
                if 0 <= ry < rows:
                    ch = col.chars[i]
                    color = head_color if i == 0 else trail_color
                    glyph = render_char(ch, color)
                    # Use x-coordinate based on the actual column index
                    x = (ci % cols) * cell_w
                    y = ry * cell_h
                    trail.blit(glyph, (x, y))

        # Blit trail to screen
        screen.blit(trail, (0, 0))
        pygame.display.flip()

    pygame.quit()


def root():
    """Entry point to run Matrix rain with sane defaults."""
    matrix_rain()


if __name__ == '__main__':
    root()

