try:
    from picamera2 import Picamera2
    _PICAMERA_AVAILABLE = True
except ImportError:
    _PICAMERA_AVAILABLE = False

from PIL import Image, ImageDraw
import threading


class _DummyCamera:
    """Stub camera for development on non-Pi hardware."""
    def __init__(self):
        self._w, self._h = 640, 480

    def set_display_size(self, w: int, h: int) -> None:
        self._w, self._h = w, h

    def get_frame(self) -> Image.Image:
        img = Image.new("RGB", (self._w, self._h), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.text((self._w // 2 - 60, self._h // 2), "[ kamera ]", fill=(120, 120, 120))
        return img

    def get_snapshot(self) -> Image.Image:
        return self.get_frame()

    def close(self) -> None:
        pass


class Camera:
    def __new__(cls):
        if not _PICAMERA_AVAILABLE:
            return _DummyCamera()
        return super().__new__(cls)

    def __init__(self):
        if not _PICAMERA_AVAILABLE:
            return
        self.picam2 = Picamera2()
        config = self.picam2.create_video_configuration(
            main={"size": (640, 480)}
        )
        self.picam2.configure(config)
        self._latest_raw: Image.Image | None = None      # flipped only
        self._latest_display: Image.Image | None = None  # flipped + fill-cropped
        self._lock = threading.Lock()
        self._display_w = 0
        self._display_h = 0
        self.picam2.start()
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def set_display_size(self, w: int, h: int) -> None:
        with self._lock:
            self._display_w = w
            self._display_h = h

    def _fill_crop(self, img: Image.Image, w: int, h: int) -> Image.Image:
        scale = max(w / img.width, h / img.height)
        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        resized = img.resize((new_w, new_h), Image.BILINEAR)
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        return resized.crop((left, top, left + w, top + h))

    def _loop(self):
        while self._running:
            try:
                img = self.picam2.capture_image("main").convert("RGB")
                flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
                with self._lock:
                    self._latest_raw = flipped
                    dw, dh = self._display_w, self._display_h
                if dw > 0 and dh > 0:
                    display = self._fill_crop(flipped, dw, dh)
                else:
                    display = flipped
                with self._lock:
                    self._latest_display = display
            except Exception:
                pass

    def get_frame(self) -> Image.Image | None:
        """Pre-processed display image (flip + fill-crop to display size)."""
        with self._lock:
            return self._latest_display

    def get_snapshot(self) -> Image.Image | None:
        """Flipped frame in original aspect ratio for photo capture."""
        with self._lock:
            return self._latest_raw

    def close(self):
        self._running = False
        self.picam2.stop()
        self.picam2.close()
