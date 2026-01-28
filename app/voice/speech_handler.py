import io
import base64
import tempfile
import os
from typing import Optional

# Optional imports - handle gracefully if not installed
try:
    import whisper
except ImportError:
    whisper = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

class SpeechHandler:
    def __init__(self):
        """Initialize speech-to-text and text-to-speech handlers."""
        # Initialize Whisper model (small model for faster processing)
        if whisper is None:
            self.whisper_model = None
            print("Warning: Whisper not installed. Speech-to-text will not be available.")
        else:
            try:
                self.whisper_model = whisper.load_model("base")
            except Exception as e:
                print(f"Warning: Could not load Whisper model: {e}")
                self.whisper_model = None
        
        # Initialize TTS engine
        if pyttsx3 is None:
            self.tts_engine = None
            print("Warning: pyttsx3 not installed. Text-to-speech will not be available.")
        else:
            try:
                self.tts_engine = pyttsx3.init()
                # Configure TTS properties
                try:
                    voices = self.tts_engine.getProperty('voices')
                    # Skip voice selection to avoid indexing issues on Windows
                    # Use default system voice
                except Exception:
                    # Continue with default voice configuration
                    pass
                self.tts_engine.setProperty('rate', 150)  # Speed of speech
                self.tts_engine.setProperty('volume', 0.9)  # Volume level
            except Exception as e:
                print(f"Warning: Could not initialize TTS: {e}")
                self.tts_engine = None
    
    def speech_to_text(self, audio_data: bytes) -> str:
        """
        Convert speech audio to text using Whisper.
        
        Args:
            audio_data: Raw audio bytes (WAV format expected)
            
        Returns:
            Transcribed text
        """
        if not self.whisper_model:
            return "Speech recognition not available. Please type your response."
        
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
            
            # Transcribe using Whisper
            result = self.whisper_model.transcribe(tmp_path, language="en")
            transcribed_text = result["text"].strip()
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            return transcribed_text
        except Exception as e:
            print(f"Error in speech-to-text: {e}")
            return f"Error transcribing audio: {str(e)}"
    
    def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert to speech
            
        Returns:
            Audio bytes (WAV format)
        """
        if not self.tts_engine:
            return b""  # Return empty bytes if TTS not available
        
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_path = tmp_file.name
            
            # Generate speech and save to file
            self.tts_engine.save_to_file(text, tmp_path)
            self.tts_engine.runAndWait()
            
            # Read the generated audio file
            with open(tmp_path, 'rb') as f:
                audio_data = f.read()
            
            # Clean up
            os.unlink(tmp_path)
            
            return audio_data
        except Exception as e:
            print(f"Error in text-to-speech: {e}")
            return b""
    
    def decode_base64_audio(self, base64_string: str) -> bytes:
        """Decode base64 encoded audio string to bytes."""
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                try:
                    parts = base64_string.split(',')
                    if len(parts) > 1:
                        base64_string = parts[1]
                except (IndexError, AttributeError):
                    # If split fails, use original string
                    pass
            
            return base64.b64decode(base64_string)
        except Exception as e:
            print(f"Error decoding base64 audio: {e}")
            return b""

# Global instance
speech_handler = SpeechHandler()
