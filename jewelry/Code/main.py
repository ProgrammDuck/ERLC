import math
import time
import ctypes
import threading
import tkinter as tk

MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE = 0x0001

center_x = 2560 /2
center_y = 1440 /2
radius = 270

steps = 360
speed = 0.0216

countdown_value = 3
root = None

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

def create_countdown_window():
    """Создает окно с отсчетом"""
    global root, countdown_value
    
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.attributes('-alpha', 0.8)
    root.overrideredirect(True)
    root.geometry('400x150+760+400')
    root.config(bg='black')
    
    label = tk.Label(
        root,
        text=f"Старт через: {countdown_value}",
        font=('Arial', 36, 'bold'),
        fg='lime',
        bg='black'
    )
    label.pack(expand=True)
    
    def update_countdown():
        global countdown_value
        if countdown_value > 0:
            label.config(text=f"Старт через: {countdown_value}")
            countdown_value -= 1
            root.after(1000, update_countdown)
        else:
            label.config(text="ПОЕХАЛИ!", fg='red')
            root.after(500, root.destroy)
    
    update_countdown()
    root.mainloop()

print("Скрипт запущен!")

overlay_thread = threading.Thread(target=create_countdown_window, daemon=True)
overlay_thread.start()

time.sleep(4)

try:
    angle = -90
    
    for i in range(steps):
        x = center_x + radius * math.cos(math.radians(angle))
        y = center_y + radius * math.sin(math.radians(angle))
        
        move_mouse(x, y)
        
        angle += 360 / steps
        
        time.sleep(speed)
    
    print("Оборот завершен!")

except KeyboardInterrupt:
    print("\nСкрипт остановлен пользователем.")