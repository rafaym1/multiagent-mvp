import os
from deepgram import Deepgram

class STT:
    def __init__(self, model="nova-3"):
        self.client = Deepgram(os.getenv("DEEPGRAM_API_KEY"))
        self.model = model

    def transcribe(self, audio_data):
        response = self.client.transcription.sync_prerecorded(
            audio_data,
            {"model": self.model, "punctuate": True},
        )
        return response.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0].get("transcript", "")
