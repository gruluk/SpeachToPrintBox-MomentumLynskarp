from picamera2 import Picamera2
from PIL import Image
import threading


class Camera:
    def __init__(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        self.picam2.configure(config)
        self._latest: Image.Image | None = None
        self._lock = threading.Lock()
        self.picam2.start()
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self._running:
            try:
                arr = self.picam2.capture_array("main")
                img = Image.fromarray(arr).convert("RGB")
                with self._lock:
                    self._latest = img
            except Exception:
                pass

    def get_frame(self) -> Image.Image | None:
        with self._lock:
            return self._latest

    def close(self):
        self._running = False
        self.picam2.stop()
        self.picam2.close()
