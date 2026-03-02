import os
import openai


def transcribe_audio(audio_path: str) -> str:
    client = openai.OpenAI()

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

    os.unlink(audio_path)
    return transcript.text
