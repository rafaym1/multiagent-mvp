import os
from openai import OpenAI

class TTS:
    def __init__(self, voice="echo"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.voice = voice

    def synthesize(self, text: str):
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=self.voice,
            input=text,
        )
        return response.stream
