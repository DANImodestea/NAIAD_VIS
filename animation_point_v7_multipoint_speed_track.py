# Updated Geospatial Animation with Extra Features

import pygame
import pandas as pd
import tkinter as tk
from tkinter import filedialog, simpledialog
from pyproj import Transformer, CRS
import sys
import datetime
import math
import os

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
FPS = 60
OCEAN_COLOR = (20, 40, 100)
PROGRESS_BAR_HEIGHT = 20
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 40
MARGIN = 10

SPEED_INCREMENT = 0.1
MIN_SPEED = 0.1
MAX_SPEED = 2.0
DEFAULT_SPEED = 1.0

# Initialize Tkinter
root = tk.Tk()
root.withdraw()

# Load a background map image (optional)
def load_map_background():
    try:
        map_img = pygame.image.load("map.png")
        return pygame.transform.scale(map_img, (WINDOW_WIDTH, WINDOW_HEIGHT))
    except:
        return None

# Column selection

def prompt_manual_column_selection(df):
    col_names = df.columns.tolist()
    x_col = simpledialog.askstring("Manual Column Selection", f"Enter X (Longitude) column:\n{col_names}")
    y_col = simpledialog.askstring("Manual Column Selection", f"Enter Y (Latitude) column:\n{col_names}")
    t_col = simpledialog.askstring("Manual Column Selection", f"Enter Time column:\n{col_names}")
    return x_col, y_col, t_col

# Load CSV and apply projection

def load_and_process_csv():
    file_path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV Files", "*.csv")])
    if not file_path:
        sys.exit("No file selected.")

    df = pd.read_csv(file_path)
    x_col, y_col, t_col = prompt_manual_column_selection(df)
    df = df.dropna(subset=[x_col, y_col, t_col])
    df[t_col] = pd.to_datetime(df[t_col])

    projection_input = simpledialog.askstring("Projection", "Enter projection (e.g., EPSG:4326)", initialvalue="EPSG:4326")
    transformer = Transformer.from_crs(CRS(projection_input), CRS("EPSG:4326"), always_xy=True)
    df['lon'], df['lat'] = zip(*df.apply(lambda row: transformer.transform(row[x_col], row[y_col]), axis=1))
    df['timestamp'] = df[t_col]

    id_col = None
    for col in df.columns:
        if "id" in col.lower():
            id_col = col
            break

    if not id_col:
        df['id'] = 0  # Single track fallback
    else:
        df['id'] = df[id_col]

    return df

# Coordinate conversion

def latlon_to_screen(lat, lon):
    x = (lon + 180) * (WINDOW_WIDTH / 360)
    y = (90 - lat) * (WINDOW_HEIGHT / 180)
    return int(x), int(y)

# Interpolation

def interpolate_points(p1, p2, t1, t2, steps=10):
    result = []
    for i in range(steps):
        f = i / steps
        lon = p1[0] + f * (p2[0] - p1[0])
        lat = p1[1] + f * (p2[1] - p1[1])
        timestamp = t1 + (t2 - t1) * f
        result.append((lon, lat, timestamp))
    return result

# Step calculation

def calculate_steps(p1, p2, t1, t2):
    dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    time_diff = (t2 - t1).total_seconds()
    return max(5, min(50, int(dist * time_diff / 1000)))

# Draw progress bar

def draw_progress_bar(screen, progress):
    progress_width = int(WINDOW_WIDTH * progress)
    pygame.draw.rect(screen, (100, 200, 100), (0, WINDOW_HEIGHT - PROGRESS_BAR_HEIGHT, progress_width, PROGRESS_BAR_HEIGHT))
    pygame.draw.rect(screen, (255, 255, 255), (0, WINDOW_HEIGHT - PROGRESS_BAR_HEIGHT, WINDOW_WIDTH, PROGRESS_BAR_HEIGHT), 2)

# Button rendering

def draw_button(screen, text, x, y, width, height, color, font):
    pygame.draw.rect(screen, color, (x, y, width, height))
    label = font.render(text, True, (255, 255, 255))
    screen.blit(label, (x + (width - label.get_width()) // 2, y + (height - label.get_height()) // 2))

# Main function

def main():
    df = load_and_process_csv()
    grouped_paths = {}
    colors = {}
    color_palette = [(255,0,0),(0,255,0),(0,0,255),(255,255,0),(0,255,255),(255,0,255)]

    for i, (track_id, group) in enumerate(df.groupby("id")):
        path = []
        group = group.sort_values("timestamp")
        for j in range(len(group) - 1):
            p1 = (group.iloc[j]['lon'], group.iloc[j]['lat'])
            p2 = (group.iloc[j+1]['lon'], group.iloc[j+1]['lat'])
            t1 = group.iloc[j]['timestamp']
            t2 = group.iloc[j+1]['timestamp']
            steps = calculate_steps(p1, p2, t1, t2)
            path.extend(interpolate_points(p1, p2, t1, t2, steps))
        grouped_paths[track_id] = path
        colors[track_id] = color_palette[i % len(color_palette)]

    all_path = sum(grouped_paths.values(), [])
    total_frames = len(all_path)

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Geospatial Point Animation")
    font = pygame.font.SysFont(None, 24)
    clock = pygame.time.Clock()
    map_bg = load_map_background()

    running = True
    frame = 0
    paused = False
    speed = DEFAULT_SPEED
    show_trail = True
    captured_frames = []
    zoom = 1.0
    pan_x, pan_y = 0, 0
    dragging = False
    drag_start = (0, 0)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click for buttons
                    x, y = event.pos
                    if WINDOW_WIDTH - BUTTON_WIDTH - 10 <= x <= WINDOW_WIDTH - 10:
                        if 10 <= y <= 10 + BUTTON_HEIGHT:
                            paused = not paused
                        elif 60 <= y <= 60 + BUTTON_HEIGHT:
                            frame = 0
                            paused = False
                        elif 110 <= y <= 110 + BUTTON_HEIGHT:
                            speed = min(speed + SPEED_INCREMENT, MAX_SPEED)
                        elif 160 <= y <= 160 + BUTTON_HEIGHT:
                            speed = max(speed - SPEED_INCREMENT, MIN_SPEED)
                        elif 210 <= y <= 210 + BUTTON_HEIGHT:
                            speed = DEFAULT_SPEED
                        elif 260 <= y <= 260 + BUTTON_HEIGHT:
                            show_trail = not show_trail
                elif event.button == 3:
                    dragging = True
                    drag_start = event.pos
                elif event.button == 4:
                    zoom = min(2.0, zoom + 0.1)
                elif event.button == 5:
                    zoom = max(0.5, zoom - 0.1)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:
                    dragging = False
            elif event.type == pygame.MOUSEMOTION and dragging:
                dx, dy = event.rel
                pan_x += dx
                pan_y += dy

        # --- Drawing ---
        if map_bg:
            screen.blit(map_bg, (0, 0))
        else:
            screen.fill(OCEAN_COLOR)

        if show_trail:
            for track_id, path in grouped_paths.items():
                for i in range(1, min(int(frame), len(path))):
                    x1, y1 = latlon_to_screen(path[i-1][1], path[i-1][0])
                    x2, y2 = latlon_to_screen(path[i][1], path[i][0])
                    pygame.draw.line(screen, colors[track_id], (x1+pan_x, y1+pan_y), (x2+pan_x, y2+pan_y), 2)

        for track_id, path in grouped_paths.items():
            if int(frame) < len(path):
                lon, lat, timestamp = path[int(frame)]
            else:
                lon, lat, timestamp = path[-1]
            x, y = latlon_to_screen(lat, lon)
            pygame.draw.circle(screen, colors[track_id], (x + pan_x, y + pan_y), 5)
            text = f"Track {track_id}, Lon: {lon:.2f}, Lat: {lat:.2f}, Time: {timestamp.strftime('%H:%M:%S')}"
            label = font.render(text, True, (255, 255, 255))
            screen.blit(label, (10, 10 + list(grouped_paths).index(track_id) * 20))

        if not paused:
            frame += speed
            if frame >= total_frames:
                frame = total_frames - 1

        draw_progress_bar(screen, frame / total_frames)

        # Buttons
        draw_button(screen, "Pause", WINDOW_WIDTH - BUTTON_WIDTH - 10, 10, BUTTON_WIDTH, BUTTON_HEIGHT, (50,150,50), font)
        draw_button(screen, "Replay", WINDOW_WIDTH - BUTTON_WIDTH - 10, 60, BUTTON_WIDTH, BUTTON_HEIGHT, (50,150,50), font)
        draw_button(screen, "Faster", WINDOW_WIDTH - BUTTON_WIDTH - 10, 110, BUTTON_WIDTH, BUTTON_HEIGHT, (50,150,50), font)
        draw_button(screen, "Slower", WINDOW_WIDTH - BUTTON_WIDTH - 10, 160, BUTTON_WIDTH, BUTTON_HEIGHT, (50,150,50), font)
        draw_button(screen, "Reset Speed", WINDOW_WIDTH - BUTTON_WIDTH - 10, 210, BUTTON_WIDTH, BUTTON_HEIGHT, (50,150,50), font)
        draw_button(screen, "Toggle Trail", WINDOW_WIDTH - BUTTON_WIDTH - 10, 260, BUTTON_WIDTH, BUTTON_HEIGHT, (100,100,200), font)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()