import ctypes
import ctypes.wintypes as wt
import numpy as np
import cv2
import time
import threading
import sys
from mss import mss

CAPTURE_REGION = (995, 564, 569, 337)
# CAPTURE_REGION = (995, 564, 569, 337) - 2K
# CAPTURE_REGION = (676, 380, 567, 346) - FullHd
GLOBAL_CLICK_COOLDOWN = 0
CLICK_OFFSET_PX = 1

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP   = 0x0004

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wt.ULONG))]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("_input", INPUT_UNION)]

def send_click():
    down = INPUT(type=0, _input=INPUT_UNION(mi=MOUSEINPUT(
        dx=0, dy=0, mouseData=0, dwFlags=MOUSEEVENTF_LEFTDOWN, time=0, dwExtraInfo=None)))
    up   = INPUT(type=0, _input=INPUT_UNION(mi=MOUSEINPUT(
        dx=0, dy=0, mouseData=0, dwFlags=MOUSEEVENTF_LEFTUP,   time=0, dwExtraInfo=None)))
    ctypes.windll.user32.SendInput(2, (INPUT * 2)(down, up), ctypes.sizeof(INPUT))


class PinDetector:
    def __init__(self):
        self.running      = False
        self.paused       = True
        self.last_click   = 0.0
        self.region       = None
        self.sct          = mss()
        self.clicked_pins = {}

    def _grab(self):
        reg = self.region or {"left": 0, "top": 0, "width": 1920, "height": 1080}
        return np.array(self.sct.grab(reg))[:, :, :3]

    def _find_line_y(self, bgr):
        b = bgr[:, :, 0].astype(np.int32)
        g = bgr[:, :, 1].astype(np.int32)
        r = bgr[:, :, 2].astype(np.int32)
        yellow = (r > 140) & (g > 100) & (b < 90) & (r > g) & (g > b + 20)
        sums   = yellow.sum(axis=1)
        best   = int(np.argmax(sums))
        return best if sums[best] >= 5 else None

    def _find_pins(self, bgr):
        b = bgr[:, :, 0].astype(np.int32)
        g = bgr[:, :, 1].astype(np.int32)
        r = bgr[:, :, 2].astype(np.int32)
        mask = (
            (np.abs(r - g) < 30) &
            (np.abs(g - b) < 30) &
            (np.abs(r - b) < 30) &
            (r > 90) & (r < 225)
        ).astype(np.uint8) * 255

        k    = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

        conts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                     cv2.CHAIN_APPROX_SIMPLE)
        return [cv2.boundingRect(c) for c in conts
                if cv2.contourArea(c) >= 400]

    def _line_inside(self, box, line_y):
        x, y, w, h = box
        from_bottom = (y + h) >= (line_y + CLICK_OFFSET_PX) and y < line_y
        from_top    = y <= (line_y - CLICK_OFFSET_PX) and (y + h) > line_y
        return from_bottom or from_top

    def tick(self):
        bgr    = self._grab()
        line_y = self._find_line_y(bgr)
        if line_y is None:
            return False, bgr, None, []

        pins       = self._find_pins(bgr)
        now        = time.time()
        clicked    = False
        current_xs = set()

        for box in pins:
            x, y, w, h = box
            cx = x + w // 2
            current_xs.add(cx)

            if self._line_inside(box, line_y):
                already = self.clicked_pins.get(cx, False)
                if not already and (now - self.last_click >= GLOBAL_CLICK_COOLDOWN):
                    send_click()
                    self.last_click       = now
                    self.clicked_pins[cx] = True
                    clicked = True
                    print(f"[CLICK] pin cx={cx} | Y={y}..{y+h} | line={line_y}")
            else:
                if cx in self.clicked_pins:
                    self.clicked_pins[cx] = False

        gone = set(self.clicked_pins.keys()) - current_xs
        for cx in gone:
            del self.clicked_pins[cx]

        return clicked, bgr, line_y, pins

    def debug_frame(self, bgr, line_y, pins, clicked):
        vis = bgr.copy()

        if line_y is not None:
            cv2.line(vis, (0, line_y), (vis.shape[1], line_y), (0, 255, 255), 2)
            cv2.putText(vis, f"LINE Y={line_y}", (4, max(line_y - 6, 14)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        for (x, y, w, h) in pins:
            cx     = x + w // 2
            inside = line_y is not None and self._line_inside((x, y, w, h), line_y)
            done   = self.clicked_pins.get(cx, False)

            if inside and done:
                col, label = (0, 165, 255), "DONE"
            elif inside:
                col, label = (0, 0, 255), "CLICK!"
            elif line_y and y > line_y:
                col, label = (0, 220, 0), f"up {y - line_y}px"
            else:
                col, label = (180, 180, 180), (f"down {line_y-(y+h)}px" if line_y else "")

            cv2.rectangle(vis, (x, y), (x + w, y + h), col, 2)
            cv2.putText(vis, label, (x, max(y - 3, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, col, 1)

        status = "CLICK!" if clicked else ("PAUSE" if self.paused else "ACTIVE")
        scol   = (0, 0, 255) if clicked else ((100, 100, 0) if self.paused else (0, 200, 0))
        cv2.putText(vis, status, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, scol, 2)
        cv2.putText(vis, f"Tracking: {len(self.clicked_pins)} pins",
                    (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        cv2.putText(vis, "F6=pause  F8=stop  ESC=close",
                    (10, vis.shape[0] - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)

        cv2.imshow("Pin Detector v5", vis)
        return cv2.waitKey(1) & 0xFF != 27

    def run(self, debug=False):
        self.running = True
        print("\n" + "=" * 54)
        print("  ER:LC house auto rob v5")
        print(f"  Click offset: {CLICK_OFFSET_PX}px | Cooldown: {GLOBAL_CLICK_COOLDOWN}s")
        print("  F6 = Start/Pause   |   F8 = Stop")
        print("=" * 54)

        if CAPTURE_REGION:
            self.region = {
                "left":   CAPTURE_REGION[0],
                "top":    CAPTURE_REGION[1],
                "width":  CAPTURE_REGION[2],
                "height": CAPTURE_REGION[3]
            }
            print(f"[INFO] Region: {CAPTURE_REGION}")
        else:
            print("[WARN] CAPTURE_REGION not set — capturing full screen")

        print(f"[INFO] Debug: {'ON' if debug else 'OFF'}")
        print("[INFO] Running...\n")

        while self.running:
            if self.paused:
                time.sleep(0.05)
                continue

            clicked, bgr, line_y, pins = self.tick()

            if debug:
                if not self.debug_frame(bgr, line_y, pins, clicked):
                    break

            time.sleep(0.016)

        cv2.destroyAllWindows()
        print("[INFO] Stopped.")


def setup_hotkeys(det: PinDetector):
    try:
        import keyboard as kb
    except ImportError:
        print("[WARN] pip install keyboard")
        return

    def toggle():
        det.paused = not det.paused
        print("[F6]", "PAUSED" if det.paused else "RUNNING")

    def stop():
        det.running = False
        det.paused  = True
        print("[F8] Stopping...")

    kb.add_hotkey("F6", toggle)
    kb.add_hotkey("F8", stop)
    print("[INFO] Hotkeys: F6=pause, F8=stop")


if __name__ == "__main__":
    DEBUG = "--debug" in sys.argv

    det = PinDetector()
    det.paused = True

    threading.Thread(target=setup_hotkeys, args=(det,), daemon=True).start()

    try:
        det.run(debug=DEBUG)
    except KeyboardInterrupt:
        det.running = False
        print("\n[INFO] Interrupted.")