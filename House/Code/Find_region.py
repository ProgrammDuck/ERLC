import cv2
import numpy as np
from mss import mss

sct = mss()
mon = sct.monitors[1]
img = np.array(sct.grab(mon))[:, :, :3]
vis = img.copy()

drawing = False
ix, iy = -1, -1
fx, fy = -1, -1

def draw(event, x, y, flags, param):
    global ix, iy, fx, fy, drawing, vis
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        vis = img.copy()
        cv2.rectangle(vis, (ix, iy), (x, y), (0, 255, 0), 2)
        cv2.putText(vis, f"({ix},{iy}) -> ({x},{y})", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        fx, fy = x, y
        vis = img.copy()
        cv2.rectangle(vis, (ix, iy), (fx, fy), (0, 0, 255), 2)
        w    = abs(fx - ix)
        h    = abs(fy - iy)
        left = min(ix, fx)
        top  = min(iy, fy)
        print("\n" + "=" * 50)
        print("Paste this into roblox_pin_autoclick.py:")
        print(f"CAPTURE_REGION = ({left}, {top}, {w}, {h})")
        print("=" * 50 + "\n")

cv2.namedWindow("Draw a box around the minigame area [ESC=quit]", cv2.WINDOW_NORMAL)
cv2.setMouseCallback("Draw a box around the minigame area [ESC=quit]", draw)

print("Draw a box around the Roblox minigame area...")
print("Then copy the CAPTURE_REGION value from the console.")

while True:
    cv2.imshow("Draw a box around the minigame area [ESC=quit]", vis)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cv2.destroyAllWindows()