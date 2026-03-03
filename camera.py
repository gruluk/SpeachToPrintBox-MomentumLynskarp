from picamera2 import Picamera2
from PIL import Image
import time


def capture_photo() -> Image.Image:
    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (1280, 720)})
    picam2.configure(config)
    picam2.start()
    time.sleep(2)  # let auto-exposure settle
    image = picam2.capture_image("main")
    picam2.stop()
    picam2.close()
    return image
