"""Reproduce the two Room background figures from the frozen main archive.

Run from any directory with Python and Pillow installed:
    python figures/part1/make_room_background.py

The script reads the Room250 configuration, map, agents and tasks directly from
Git commit b4293f603198f89577e90db2c4f0d3b31fdaced2. This commit is a parent of
the report's main branch and contains the frozen experiment-materials archive.
No simulation output or experimental performance data are used.

The first figure plots every one of the 250 initial locations. Its inset is a
literal crop of the same grid, including the same robot starts.

The second figure uses robot 0 and initially visible task 1, both zero-based.
Task 1 is the first visible task whose two single-agent shortest grid paths
share only the pickup cell. This selection makes the two stages readable.
The routes are computed by breadth-first search with fixed neighbor order
east, south, west, north. They minimize grid moves and ignore turns, timing,
other robots and assignment scoring. The pairing is an illustration, not an
observed scheduler assignment or a replay.

Coordinates in the PNG metadata are zero-based (row, column). Each raster is
2560 x 1600 pixels at 300 dpi. Fonts prefer Arial on Windows, with DejaVu Sans
as a portable fallback. PNG metadata records provenance and the chosen inputs.
"""

from collections import deque
import hashlib
import json
import math
from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCE_COMMIT = "b4293f603198f89577e90db2c4f0d3b31fdaced2"
SOURCE_DIR = "experiment-materials/网络协议方向/harness/data/pkg/maps/room"
WIDTH, HEIGHT, SCALE = 2560, 1600, 2
MAP_X, MAP_Y, MAP_SIDE = 50, 110, 1440
INK, WALL, ROBOT = "#182129", "#89959f", "#1c5477"
BLUE, AMBER = "#17628e", "#a55511"
WHITE, GRID = "#ffffff", "#e2e6e9"


def git_bytes(name):
    path = f"{SOURCE_DIR}/{name}"
    try:
        return subprocess.check_output(
            ["git", "show", f"{SOURCE_COMMIT}:{path}"], cwd=ROOT
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(
            f"The frozen input {path} is unavailable. Fetch the repository's "
            f"main history containing {SOURCE_COMMIT}."
        ) from error


def input_lines(data):
    return [
        line.strip()
        for line in data.decode("utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def load_inputs():
    raw_config = git_bytes("room250.json")
    config = json.loads(raw_config)
    raw_map = git_bytes(config["mapFile"])
    raw_agents = git_bytes(config["agentFile"])
    raw_tasks = git_bytes(config["taskFile"])

    lines = input_lines(raw_map)
    height = int(lines[1].split()[1])
    width = int(lines[2].split()[1])
    grid = lines[lines.index("map") + 1 :]
    assert height == width == 64
    assert len(grid) == height and all(len(row) == width for row in grid)

    lines = input_lines(raw_agents)
    assert len(lines) - 1 == int(lines[0])
    starts = [int(value) for value in lines[1 : config["teamSize"] + 1]]
    assert config["teamSize"] == len(starts) == len(set(starts)) == 250

    lines = input_lines(raw_tasks)
    tasks = [tuple(int(value) for value in line.split(",")) for line in lines[1:]]
    assert len(tasks) == int(lines[0]) == 1375
    assert all(len(task) == 2 for task in tasks)
    assert all(grid[location // width][location % width] == "." for location in starts)
    assert sum(row.count(".") for row in grid) == 3646

    digests = {
        name: hashlib.sha256(data).hexdigest()
        for name, data in (
            ("room250.json", raw_config),
            (config["mapFile"], raw_map),
            (config["agentFile"], raw_agents),
            (config["taskFile"], raw_tasks),
        )
    }
    return grid, starts, tasks, config, digests


def shortest_path(grid, start, goal):
    width, height = len(grid[0]), len(grid)
    previous = {start: None}
    pending = deque([start])
    while pending and goal not in previous:
        location = pending.popleft()
        row, column = divmod(location, width)
        for drow, dcolumn in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            next_row, next_column = row + drow, column + dcolumn
            if not (0 <= next_row < height and 0 <= next_column < width):
                continue
            candidate = next_row * width + next_column
            if grid[next_row][next_column] == "." and candidate not in previous:
                previous[candidate] = location
                pending.append(candidate)
    if goal not in previous:
        raise ValueError("A chosen endpoint is unreachable.")
    path = [goal]
    while path[-1] != start:
        path.append(previous[path[-1]])
    return list(reversed(path))


def choose_task(grid, start, tasks, visible_count):
    for index, (pickup, delivery) in enumerate(tasks[:visible_count]):
        first = shortest_path(grid, start, pickup)
        second = shortest_path(grid, pickup, delivery)
        if set(first).intersection(second) == {pickup}:
            return index, first, second
    raise ValueError("No initially visible task gives two distinct path segments.")


def font(size, bold=False):
    names = (
        ["C:/Windows/Fonts/arialbd.ttf", "DejaVuSans-Bold.ttf"]
        if bold
        else ["C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf"]
    )
    for name in names:
        try:
            return ImageFont.truetype(name, round(size * SCALE))
        except OSError:
            continue
    raise RuntimeError("Install Arial or DejaVu Sans to reproduce the figures.")


def point(x, y):
    return x * SCALE, y * SCALE


def box(left, top, right, bottom):
    return left * SCALE, top * SCALE, right * SCALE, bottom * SCALE


def text(draw, x, y, value, size=42, bold=False, anchor="la", fill=INK):
    draw.text(point(x, y), value, font=font(size, bold), fill=fill, anchor=anchor)


def stroke(draw, points, fill, width):
    draw.line([point(x, y) for x, y in points], fill=fill, width=round(width * SCALE))


def dashed_line(draw, points, fill, width=4, dash=15, gap=10):
    phase = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        distance = math.hypot(x2 - x1, y2 - y1)
        offset = 0.0
        while offset < distance:
            active = phase < dash
            boundary = dash if active else dash + gap
            length = min(distance - offset, boundary - phase)
            if active:
                start = offset / distance
                end = (offset + length) / distance
                stroke(
                    draw,
                    [(x1 + start * (x2 - x1), y1 + start * (y2 - y1)),
                     (x1 + end * (x2 - x1), y1 + end * (y2 - y1))],
                    fill,
                    width,
                )
            offset += length
            phase = (phase + length) % (dash + gap)


def circle(draw, x, y, radius, fill, outline=WHITE, width=1.5):
    draw.ellipse(
        box(x - radius, y - radius, x + radius, y + radius),
        fill=fill, outline=outline, width=round(width * SCALE),
    )


def marker(draw, x, y, kind, radius=15):
    if kind == "start":
        circle(draw, x, y, radius, INK, width=2.5)
    elif kind == "pickup":
        draw.rectangle(
            box(x - radius, y - radius, x + radius, y + radius),
            fill=WHITE, outline=AMBER, width=round(5 * SCALE),
        )
    elif kind == "delivery":
        vertices = []
        for index in range(10):
            angle = -math.pi / 2 + index * math.pi / 5
            length = radius if index % 2 == 0 else radius * 0.43
            vertices.append(point(x + length * math.cos(angle), y + length * math.sin(angle)))
        draw.polygon(vertices, fill=AMBER, outline=WHITE, width=round(1.5 * SCALE))


def draw_map(draw, grid, starts=(), origin=(MAP_X, MAP_Y), side=MAP_SIDE,
             window=(0, 0, 64, 64), detail_grid=False):
    top, left, bottom, right = window
    cell = side / (right - left)
    x0, y0 = origin
    for row in range(top, bottom):
        for column in range(left, right):
            if grid[row][column] != ".":
                draw.rectangle(
                    box(x0 + (column - left) * cell,
                        y0 + (row - top) * cell,
                        x0 + (column - left + 1) * cell,
                        y0 + (row - top + 1) * cell), fill=WALL,
                )
    if detail_grid:
        for index in range(right - left + 1):
            coordinate = index * cell
            stroke(draw, [(x0 + coordinate, y0), (x0 + coordinate, y0 + side)], GRID, 0.6)
            stroke(draw, [(x0, y0 + coordinate), (x0 + side, y0 + coordinate)], GRID, 0.6)
    for location in starts:
        row, column = divmod(location, len(grid[0]))
        if top <= row < bottom and left <= column < right:
            circle(draw, x0 + (column - left + 0.5) * cell,
                   y0 + (row - top + 0.5) * cell,
                   cell * 0.23, ROBOT, width=max(1, cell * 0.045))
    draw.rectangle(box(x0, y0, x0 + side, y0 + side), outline=GRID, width=SCALE)


def map_point(location):
    row, column = divmod(location, 64)
    return MAP_X + (column + 0.5) * MAP_SIDE / 64, MAP_Y + (row + 0.5) * MAP_SIDE / 64


def arrow(draw, x, y, dx, dy, fill, size=13):
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    vertices = [
        point(x + ux * size * 0.7, y + uy * size * 0.7),
        point(x - ux * size * 0.55 - uy * size * 0.52,
              y - uy * size * 0.55 + ux * size * 0.52),
        point(x - ux * size * 0.55 + uy * size * 0.52,
              y - uy * size * 0.55 - ux * size * 0.52),
    ]
    draw.polygon(vertices, fill=fill)


def draw_route(draw, path, fill, dashed=False):
    points = [map_point(location) for location in path]
    stroke(draw, points, WHITE, 10)
    if dashed:
        dashed_line(draw, points, fill, width=5, dash=13, gap=8)
    else:
        stroke(draw, points, fill, 5)
    straight_indices = [
        index for index in range(1, len(path) - 1)
        if path[index] - path[index - 1] == path[index + 1] - path[index]
    ]
    for fraction in (0.33, 0.7):
        index = min(straight_indices, key=lambda value: abs(value - fraction * len(path)))
        x, y = map_point(path[index])
        previous_x, previous_y = map_point(path[index - 1])
        arrow(draw, x, y, x - previous_x, y - previous_y, fill, 12)


def new_canvas():
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), WHITE)
    return image, ImageDraw.Draw(image)


def save(image, filename, provenance):
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Source", json.dumps(provenance, ensure_ascii=False, sort_keys=True))
    image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(
        OUT / filename, dpi=(300, 300), pnginfo=metadata
    )


def starting_positions_figure(grid, starts, provenance):
    image, draw = new_canvas()
    text(draw, 50, 28, "Room layout and 250 robot starts", size=49, bold=True)
    draw_map(draw, grid, starts)

    window = (11, 31, 23, 43)
    text(draw, 1675, 112, "Doorway detail", size=44, bold=True)
    draw_map(draw, grid, starts, origin=(1675, 190), side=780,
             window=window, detail_grid=True)
    door_row, door_column = 16, 37
    assert grid[door_row][door_column - 1 : door_column + 2] == "@.@"
    detail_cell = 780 / 12
    door_x = 1675 + (door_column - window[1] + 0.5) * detail_cell
    door_top = 190 + (door_row - window[0]) * detail_cell
    text(draw, 2185, 382, "Door", size=42)
    stroke(draw, [(2185, 435), (door_x, door_top - 7)], INK, 2)
    cell = MAP_SIDE / 64
    top, left, bottom, right = window
    corners = [(MAP_X + left * cell, MAP_Y + top * cell),
               (MAP_X + right * cell, MAP_Y + top * cell),
               (MAP_X + right * cell, MAP_Y + bottom * cell),
               (MAP_X + left * cell, MAP_Y + bottom * cell)]
    dashed_line(draw, corners + corners[:1], INK, width=2.8, dash=13, gap=10)

    draw.rectangle(box(1680, 1088, 1728, 1136), fill=WALL)
    text(draw, 1762, 1088, "Wall", size=43)
    circle(draw, 1704, 1230, 18, ROBOT)
    text(draw, 1762, 1205, "Robot start", size=43)
    stroke(draw, [(1680, 1395), (1745, 1395)], INK, 3)
    stroke(draw, [(1680, 1384), (1680, 1406)], INK, 3)
    stroke(draw, [(1745, 1384), (1745, 1406)], INK, 3)
    text(draw, 1780, 1370, "1 cell in detail", size=40)
    save(image, "p1_room250_starts.png", provenance)


def task_route_figure(grid, first, second, provenance):
    image, draw = new_canvas()
    text(draw, 50, 28, "An illustrative pickup–delivery route", size=49, bold=True)
    draw_map(draw, grid)
    draw_route(draw, first, BLUE, dashed=True)
    draw_route(draw, second, AMBER)
    endpoints = [("start", first[0]), ("pickup", first[-1]), ("delivery", second[-1])]
    for kind, location in endpoints:
        marker(draw, *map_point(location), kind, radius=17 if kind == "delivery" else 12)

    for (kind, _), y in zip(endpoints, (245, 720, 1195)):
        marker(draw, 1710, y + 23, kind, radius=28 if kind == "delivery" else 21)
        text(draw, 1790, y - 5, kind.capitalize(), size=47, bold=True)

    dashed_line(draw, [(1710, 350), (1710, 625)], BLUE, width=6, dash=20, gap=14)
    arrow(draw, 1710, 629, 0, 1, BLUE, 22)
    text(draw, 1790, 460, "To pickup", size=42, fill=BLUE)
    stroke(draw, [(1710, 825), (1710, 1100)], AMBER, 6)
    arrow(draw, 1710, 1104, 0, 1, AMBER, 22)
    text(draw, 1790, 935, "To delivery", size=42, fill=AMBER)
    save(image, "p1_room250_task_route.png", provenance)


def main():
    grid, starts, tasks, config, digests = load_inputs()
    visible_count = int(config["numTasksReveal"] * config["teamSize"])
    task_index, first, second = choose_task(grid, starts[0], tasks, visible_count)
    provenance = {
        "commit": SOURCE_COMMIT,
        "input_directory": SOURCE_DIR,
        "sha256": digests,
        "configuration": "room250.json",
        "robot_count": len(starts),
        "initially_visible_tasks": visible_count,
        "inset_rows_columns_end_exclusive": [11, 31, 23, 43],
    }
    starting_positions_figure(grid, starts, provenance)
    route_provenance = dict(provenance)
    route_provenance.update({
        "robot_id_zero_based": 0,
        "task_id_zero_based": task_index,
        "start_row_column": divmod(first[0], 64),
        "pickup_row_column": divmod(first[-1], 64),
        "delivery_row_column": divmod(second[-1], 64),
        "route_type": "single-agent shortest grid paths, illustrative pairing",
        "neighbor_order": ["east", "south", "west", "north"],
        "route_start_to_pickup": first,
        "route_pickup_to_delivery": second,
    })
    task_route_figure(grid, first, second, route_provenance)
    print(json.dumps({
        "output": [str(OUT / "p1_room250_starts.png"), str(OUT / "p1_room250_task_route.png")],
        "size": [WIDTH, HEIGHT],
        "source_commit": SOURCE_COMMIT,
        "robot_id": 0,
        "task_id": task_index,
        "initially_visible_tasks": visible_count,
        "route_moves": [len(first) - 1, len(second) - 1],
    }, indent=2))


if __name__ == "__main__":
    main()
