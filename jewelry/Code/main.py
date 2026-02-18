import math
import json
import time
import ctypes
import keyboard

MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001

with open("config.json") as f:
    config = json.load(f)

Start_keybind = config["Jewelry"]["START"].lower()
Close_keybind = config["Jewelry"]["CLOSE"].lower()

user32 = ctypes.windll.user32
center_x = user32.GetSystemMetrics(0) / 2 
center_y = user32.GetSystemMetrics(1) / 2 
print(f"{center_x}x{center_y} --- center,\n{center_x*2}x{center_y*2} --- resolution")

radius = 270
steps = 360
speed = 0.0216

running = False
exit_flag = False

def move_mouse(x, y):
    screen_width = ctypes.windll.user32.GetSystemMetrics(0)
    screen_height = ctypes.windll.user32.GetSystemMetrics(1)
    
    absolute_x = int(x * 65535 / screen_width)
    absolute_y = int(y * 65535 / screen_height)
    
    ctypes.windll.user32.mouse_event(
        MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE,
        absolute_x,
        absolute_y,
        0,
        0
    )

def on_start_press():
    global running
    running = not running
    if running:
        print("Started!")
    else:
        print("Stopped!")

def on_close_press():
    global exit_flag
    print("Script stopped.")
    exit_flag = True

keyboard.add_hotkey(Start_keybind, on_start_press)
keyboard.add_hotkey(Close_keybind, on_close_press)

print("Script ready!")
print(f"Press {Start_keybind.upper()} to start/stop")
print(f"Press {Close_keybind.upper()} to exit")

try:
    while not exit_flag:
        if running:
            angle = -90
            
            for i in range(steps):
                if not running or exit_flag:
                    break
                    
                x = center_x + radius * math.cos(math.radians(angle))
                y = center_y + radius * math.sin(math.radians(angle))
                
                move_mouse(x, y)
                
                angle += 360 / steps
                
                time.sleep(speed)
            
            if running:
                print("Cycle completed")
                running = False
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nScript stopped.")