import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os

SAMPLE_RATE = 44100


class AudioRecorder:
    def __init__(self):
        self._frames = []
        self._recording = False
        self._stream = None

    def start(self):
        self._frames = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def _callback(self, indata, frames, time, status):
        if self._recording:
            self._frames.append(indata.copy())

    def stop(self) -> str | None:
        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            return None

        audio_data = np.concatenate(self._frames, axis=0)
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav.write(temp_file.name, SAMPLE_RATE, audio_data)
        return temp_file.name
