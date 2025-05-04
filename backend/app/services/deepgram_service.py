import logging
from typing import Optional
from deepgram import DeepgramClient, DeepgramClientOptions, SpeakOptions
from ..config import DEEPGRAM_API_KEY

class DeepgramService:
    def __init__(self):
        try:
            dg_config = DeepgramClientOptions(verbose=logging.WARNING)
            self.deepgram_client = DeepgramClient(DEEPGRAM_API_KEY, dg_config)
            logging.info("Deepgram client initialized in DeepgramService.")
        except Exception as e:
            logging.error(f"Deepgram client initialization failed: {e}")
            self.deepgram_client = None

    async def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        if not self.deepgram_client or not audio_data:
            logging.error("Deepgram client not initialized or no audio data provided.")
            return None
        try:
            source = {'buffer': audio_data, 'mimetype': 'audio/wav'}
            options = {"punctuate": True, "model": "nova-2", "language": "en-US"}
            logging.info("Sending audio buffer to Deepgram for transcription...")
            response = self.deepgram_client.listen.prerecorded.v("1").transcribe_file(source, options)
            if response and hasattr(response, 'results'):
                transcript = response.results.channels[0].alternatives[0].transcript
                logging.info(f"Transcription received: {transcript[:50]}...")
                return transcript
            else:
                logging.error(f"Unexpected Deepgram transcription response format: {response}")
                return None
        except Exception as e:
            logging.error(f"Deepgram transcription error: {e}")
            return None

    async def synthesize_speech(self, text: str) -> Optional[bytes]:
        if not self.deepgram_client or not text:
            logging.error("Deepgram client not initialized or no text provided.")
            return None
        try:
            SPEAK_OPTIONS = {"text": text}
            options = SpeakOptions(
                model="aura-asteria-en",
                encoding="linear16",
                container="wav"
            )
            logging.info(f"Sending text to Deepgram for synthesis: {text[:50]}...")
            response = self.deepgram_client.speak.v("1").stream(SPEAK_OPTIONS, options)
            if response and hasattr(response, 'stream') and response.stream:
                audio_bytes = response.stream.read()
                logging.info("Speech synthesis received.")
                return audio_bytes
            else:
                logging.error("Invalid response or stream from Deepgram TTS.")
                return None
        except Exception as e:
            logging.error(f"Deepgram synthesis error: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            return None 