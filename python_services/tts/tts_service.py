"""Text-to-speech service with support for Azure TTS, Google TTS, and Coqui TTS.

Prioritizes Azure Neural Farsi voices for best quality, falls back to Coqui TTS for offline use.
"""
from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SynthesizedAudio:
    text: str
    encoding: str
    payload: bytes
    sample_rate: int = 22050

    def as_base64(self) -> str:
        return base64.b64encode(self.payload).decode("utf-8")


class TextToSpeechService:
    """Text-to-speech service with multiple provider support.
    
    Supports:
    - Azure Cognitive Services (best quality, requires API key)
    - Google Cloud TTS (requires API key)
    - Coqui TTS (offline, local models)
    """
    
    def __init__(self, provider: str = "auto"):
        """
        Initialize TTS service.
        
        Args:
            provider: "azure", "google", "coqui", or "auto" (try azure -> google -> coqui)
        """
        self.provider = provider
        self.azure_client = None
        self.google_client = None
        self.coqui_model = None
        self.cache: dict[str, SynthesizedAudio] = {}  # Simple in-memory cache
        
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available TTS providers."""
        # Try Azure first
        if self.provider in ("auto", "azure"):
            try:
                azure_key = os.getenv("AZURE_SPEECH_KEY")
                azure_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
                
                if azure_key:
                    import azure.cognitiveservices.speech as speechsdk
                    self.azure_client = speechsdk.SpeechConfig(
                        subscription=azure_key,
                        region=azure_region
                    )
                    # Use Farsi neural voice
                    self.azure_client.speech_synthesis_voice_name = "fa-IR-DilaraNeural"
                    logger.info("Azure TTS initialized")
                    if self.provider == "azure":
                        return
                else:
                    logger.warning("Azure TTS key not found")
            except ImportError:
                logger.warning("azure-cognitiveservices-speech not installed")
            except Exception as e:
                logger.error(f"Error initializing Azure TTS: {e}")
        
        # Try Google Cloud
        if self.provider in ("auto", "google"):
            try:
                google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if google_creds and os.path.exists(google_creds):
                    from google.cloud import texttospeech
                    self.google_client = texttospeech.TextToSpeechClient()
                    logger.info("Google Cloud TTS initialized")
                    if self.provider == "google":
                        return
                else:
                    logger.warning("Google Cloud credentials not found")
            except ImportError:
                logger.warning("google-cloud-texttospeech not installed")
            except Exception as e:
                logger.error(f"Error initializing Google TTS: {e}")
        
        # Fallback to Coqui TTS (offline)
        if self.provider in ("auto", "coqui"):
            try:
                from TTS.api import TTS
                # Use Farsi model if available, otherwise use multilingual
                try:
                    self.coqui_model = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
                    logger.info("Coqui TTS initialized (multilingual)")
                except:
                    # Fallback to basic model
                    self.coqui_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
                    logger.info("Coqui TTS initialized (English fallback)")
            except ImportError:
                logger.warning("Coqui TTS not installed, using stub mode")
            except Exception as e:
                logger.error(f"Error initializing Coqui TTS: {e}")
    
    def synthesize(self, text: str, voice: str = "fa-IR-Standard-A", use_cache: bool = True) -> SynthesizedAudio:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice: Voice name (provider-specific)
            use_cache: Whether to use cached results
            
        Returns:
            SynthesizedAudio with audio data
        """
        normalized = text.strip()
        if not normalized:
            return SynthesizedAudio(text="", encoding="audio/wav", payload=b"", sample_rate=22050)
        
        # Check cache
        cache_key = f"{normalized}:{voice}"
        if use_cache and cache_key in self.cache:
            logger.debug(f"Using cached TTS for: {normalized[:50]}...")
            return self.cache[cache_key]
        
        # Try providers in order
        result = None
        
        if self.azure_client:
            result = self._synthesize_azure(normalized, voice)
        
        if result is None and self.google_client:
            result = self._synthesize_google(normalized, voice)
        
        if result is None and self.coqui_model:
            result = self._synthesize_coqui(normalized, voice)
        
        # Fallback to stub
        if result is None:
            logger.warning("No TTS provider available, using stub")
            result = SynthesizedAudio(
                text=normalized,
                encoding="text/utf-8",
                payload=normalized.encode("utf-8"),
                sample_rate=22050
            )
        
        # Cache result
        if use_cache:
            self.cache[cache_key] = result
        
        return result
    
    def _synthesize_azure(self, text: str, voice: str) -> Optional[SynthesizedAudio]:
        """Synthesize using Azure TTS."""
        try:
            import azure.cognitiveservices.speech as speechsdk
            import io
            
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.azure_client)
            
            # Use SSML for better control
            ssml = f"""
            <speak version='1.0' xml:lang='fa-IR' xmlns='http://www.w3.org/2001/10/synthesis'>
                <voice name='fa-IR-DilaraNeural'>
                    {text}
                </voice>
            </speak>
            """
            
            result = synthesizer.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                return SynthesizedAudio(
                    text=text,
                    encoding="audio/wav",
                    payload=audio_data,
                    sample_rate=24000  # Azure default
                )
            else:
                logger.error(f"Azure TTS failed: {result.reason}")
                return None
        except Exception as e:
            logger.error(f"Error in Azure TTS: {e}", exc_info=True)
            return None
    
    def _synthesize_google(self, text: str, voice: str) -> Optional[SynthesizedAudio]:
        """Synthesize using Google Cloud TTS."""
        try:
            from google.cloud import texttospeech
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Use Farsi voice
            voice_config = texttospeech.VoiceSelectionParams(
                language_code="fa-IR",
                name="fa-IR-Standard-A",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            response = self.google_client.synthesize_speech(
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config
            )
            
            return SynthesizedAudio(
                text=text,
                encoding="audio/mp3",
                payload=response.audio_content,
                sample_rate=24000
            )
        except Exception as e:
            logger.error(f"Error in Google TTS: {e}", exc_info=True)
            return None
    
    def _synthesize_coqui(self, text: str, voice: str) -> Optional[SynthesizedAudio]:
        """Synthesize using Coqui TTS (offline)."""
        try:
            import io
            import soundfile as sf
            import numpy as np
            
            # Generate speech
            wav = self.coqui_model.tts(text=text, language="fa" if "fa" in self.coqui_model.languages else "en")
            
            # Convert to bytes
            buffer = io.BytesIO()
            sf.write(buffer, wav, samplerate=22050, format="WAV")
            audio_bytes = buffer.getvalue()
            
            return SynthesizedAudio(
                text=text,
                encoding="audio/wav",
                payload=audio_bytes,
                sample_rate=22050
            )
        except Exception as e:
            logger.error(f"Error in Coqui TTS: {e}", exc_info=True)
            return None
    
    def clear_cache(self):
        """Clear the TTS cache."""
        self.cache.clear()
