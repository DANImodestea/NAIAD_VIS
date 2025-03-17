import pygame
import pandas as pd
import tkinter as tk
from tkinter import filedialog, simpledialog
from pyproj import Transformer, CRS
import sys
import datetime
import math

# Constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
FPS = 60  # Frames per second (for clock)
OCEAN_COLOR = (20, 40, 100)
PROGRESS_BAR_HEIGHT = 20  # Height of the progress bar
BUTTON_WIDTH = 120
BUTTON_HEIGHT = 50

# Speed settings
SPEED_INCREMENT = 0.1
MIN_SPEED = 0.1
MAX_SPEED = 2.0
DEFAULT_SPEED = 1.0

# Initialize Tkinter
root = tk.Tk()
root.withdraw()  # Hide the main Tkinter window

def prompt_manual_column_selection(df):
    col_names = df.columns.tolist()
    x_col = simpledialog.askstring("Manual Column Selection", f"Enter X (Longitude) column:\n{col_names}")
    y_col = simpledialog.askstring("Manual Column Selection", f"Enter Y (Latitude) column:\n{col_names}")
    t_col = simpledialog.askstring("Manual Column Selection", f"Enter Time column:\n{col_names}")
    return x_col, y_col, t_col

def load_and_process_csv():
    file_path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV Files", "*.csv")])
    if not file_path:
        sys.exit("No file selected.")

    df = pd.read_csv(file_path)

    # Manually prompt for column names
    x_col, y_col, t_col = prompt_manual_column_selection(df)

    # Make sure there are no missing values in the selected columns
    df = df.dropna(subset=[x_col, y_col, t_col])
    df[t_col] = pd.to_datetime(df[t_col])  # Ensure the time column is in datetime format

    # Ask for projection info
    projection_input = simpledialog.askstring("Projection", "Enter projection (e.g., EPSG:4326)", initialvalue="EPSG:4326")
    transformer = Transformer.from_crs(CRS(projection_input), CRS("EPSG:4326"), always_xy=True)

    # Apply projection transformation
    df['lon'], df['lat'] = zip(*df.apply(lambda row: transformer.transform(row[x_col], row[y_col]), axis=1))
    df['timestamp'] = df[t_col]

    id_col = None
    for col in df.columns:
        if "id" in col.lower():
            id_col = col
            break

    return df[['lon', 'lat', 'timestamp']] if not id_col else df[['lon', 'lat', 'timestamp', id_col]]

def latlon_to_screen(lat, lon):
    # Convert lat/lon to screen coordinates
    x = (lon + 180) * (WINDOW_WIDTH / 360)
    y = (90 - lat) * (WINDOW_HEIGHT / 180)
    return int(x), int(y)

def interpolate_points(p1, p2, t1, t2, steps=10):
    result = []
    for i in range(steps):
        f = i / steps
        lon = p1[0] + f * (p2[0] - p1[0])
        lat = p1[1] + f * (p2[1] - p1[1])
        timestamp = t1 + (t2 - t1) * f
        result.append((lon, lat, timestamp))
    return result

def calculate_steps(p1, p2, t1, t2):
    dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    time_diff = (t2 - t1).total_seconds()
    return max(5, min(50, int(dist * time_diff / 1000)))

def draw_background(screen):
    screen.fill(OCEAN_COLOR)
    for lon in range(-180, 181, 30):
        x, _ = latlon_to_screen(0, lon)
        pygame.draw.line(screen, (30, 60, 130), (x, 0), (x, WINDOW_HEIGHT), 1)
    for lat in range(-90, 91, 30):
        _, y = latlon_to_screen(lat, 0)
        pygame.draw.line(screen, (30, 60, 130), (0, y), (WINDOW_WIDTH, y), 1)

def draw_progress_bar(screen, progress):
    # Draw the progress bar at the bottom of the screen
    progress_width = int(WINDOW_WIDTH * progress)
    pygame.draw.rect(screen, (100, 200, 100), (0, WINDOW_HEIGHT - PROGRESS_BAR_HEIGHT, progress_width, PROGRESS_BAR_HEIGHT))
    pygame.draw.rect(screen, (255, 255, 255), (0, WINDOW_HEIGHT - PROGRESS_BAR_HEIGHT, WINDOW_WIDTH, PROGRESS_BAR_HEIGHT), 3)  # Border

def draw_button(screen, text, x, y, width, height, color, font):
    # Draw a rectangle for the button
    pygame.draw.rect(screen, color, (x, y, width, height))
    # Draw the text in the center of the button
    label = font.render(text, True, (255, 255, 255))
    screen.blit(label, (x + (width - label.get_width()) // 2, y + (height - label.get_height()) // 2))

def main():
    data = load_and_process_csv()
    path = []
    for i in range(len(data) - 1):
        p1 = (data.loc[i, 'lon'], data.loc[i, 'lat'])
        p2 = (data.loc[i+1, 'lon'], data.loc[i+1, 'lat'])
        t1 = data.loc[i, 'timestamp']
        t2 = data.loc[i+1, 'timestamp']
        steps = calculate_steps(p1, p2, t1, t2)
        path.extend(interpolate_points(p1, p2, t1, t2, steps))

    pygame.init()  # Initialize pygame
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Geospatial Point Animation")
    clock = pygame.time.Clock()  # Create clock for controlling the frame rate
    font = pygame.font.SysFont(None, 36)  # Font for displaying text

    running = True
    frame = 0  # Animation starts from frame 0
    paused = False  # Whether the animation is paused
    speed = DEFAULT_SPEED  # Initial speed of the animation (1 is normal speed)

    while running:
        # --- Handle Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                # Check if Pause button was clicked
                if WINDOW_WIDTH - BUTTON_WIDTH - 10 <= x <= WINDOW_WIDTH - 10 and 10 <= y <= 10 + BUTTON_HEIGHT:
                    paused = not paused
                # Check if Replay button was clicked
                if WINDOW_WIDTH - BUTTON_WIDTH - 10 <= x <= WINDOW_WIDTH - 10 and 70 <= y <= 70 + BUTTON_HEIGHT:
                    frame = 0
                    paused = False
                # Check if Increase Speed button was clicked
                if WINDOW_WIDTH - BUTTON_WIDTH - 10 <= x <= WINDOW_WIDTH - 10 and 140 <= y <= 140 + BUTTON_HEIGHT:
                    speed = min(speed + SPEED_INCREMENT, MAX_SPEED)
                # Check if Decrease Speed button was clicked
                if WINDOW_WIDTH - BUTTON_WIDTH - 10 <= x <= WINDOW_WIDTH - 10 and 210 <= y <= 210 + BUTTON_HEIGHT:
                    speed = max(speed - SPEED_INCREMENT, MIN_SPEED)
                # Check if Reset Speed button was clicked
                if WINDOW_WIDTH - BUTTON_WIDTH - 10 <= x <= WINDOW_WIDTH - 10 and 280 <= y <= 280 + BUTTON_HEIGHT:
                    speed = DEFAULT_SPEED

        # --- Draw Background ---
        draw_background(screen)

        # --- Draw the animation or the last point ---
        if not paused:
            if frame < len(path):
                lon, lat, timestamp = path[int(frame)]  # Ensure frame is an integer
                x, y = latlon_to_screen(lat, lon)
                pygame.draw.circle(screen, (255, 0, 0), (x, y), 6)

                text = f"Lon: {lon:.4f}, Lat: {lat:.4f}, Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                label = font.render(text, True, (255, 255, 255))
                screen.blit(label, (10, 10))  # Render the text on the screen

                frame += speed  # Increase frame by speed factor
                if frame >= len(path):
                    frame = len(path) - 1
            else:
                # Once the animation finishes, stop and display the final point without further frame updates
                lon, lat, timestamp = path[-1]
                x, y = latlon_to_screen(lat, lon)
                pygame.draw.circle(screen, (255, 0, 0), (x, y), 6)

                text = f"Lon: {lon:.4f}, Lat: {lat:.4f}, Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                label = font.render(text, True, (255, 255, 255))
                screen.blit(label, (10, 10))  # Render the text on the screen

                # Do not update the frame number; keep it at the last point
                frame = len(path) - 1  # This keeps the frame on the final point
        else:
            # Ensure the last point and data stay visible during pause
            lon, lat, timestamp = path[int(frame) - 1] if frame > 0 else path[0]
            x, y = latlon_to_screen(lat, lon)
            pygame.draw.circle(screen, (255, 0, 0), (x, y), 6)

            text = f"Lon: {lon:.4f}, Lat: {lat:.4f}, Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            label = font.render(text, True, (255, 255, 255))
            screen.blit(label, (10, 10))  # Render the text on the screen

        # --- Draw Progress Bar ---
        progress = frame / len(path)  # Calculate the progress as a ratio of current frame to total frames
        draw_progress_bar(screen, progress)

        # --- Draw Buttons ---
        draw_button(screen, "Pause", WINDOW_WIDTH - BUTTON_WIDTH - 10, 10, BUTTON_WIDTH, BUTTON_HEIGHT, (50, 150, 50), font)
        draw_button(screen, "Replay", WINDOW_WIDTH - BUTTON_WIDTH - 10, 70, BUTTON_WIDTH, BUTTON_HEIGHT, (50, 150, 50), font)
        draw_button(screen, "Increase Speed", WINDOW_WIDTH - BUTTON_WIDTH - 10, 140, BUTTON_WIDTH, BUTTON_HEIGHT, (50, 150, 50), font)
        draw_button(screen, "Decrease Speed", WINDOW_WIDTH - BUTTON_WIDTH - 10, 210, BUTTON_WIDTH, BUTTON_HEIGHT, (50, 150, 50), font)
        draw_button(screen, "Reset Speed", WINDOW_WIDTH - BUTTON_WIDTH - 10, 280, BUTTON_WIDTH, BUTTON_HEIGHT, (50, 150, 50), font)

        # --- Display speed info ---
        speed_info = f"Speed: {speed:.1f}x"
        speed_label = font.render(speed_info, True, (255, 255, 255))
        screen.blit(speed_label, (WINDOW_WIDTH - 160, 350))  # Display speed info

        pygame.display.flip()  # Update the screen
        clock.tick(FPS)  # Cap the frame rate to FPS

    pygame.quit()


if __name__ == "__main__":
    main()