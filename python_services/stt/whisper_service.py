"""Whisper-based transcription service with Farsi support.

Supports both OpenAI Whisper and faster-whisper for high-quality Farsi STT.
Falls back to stub mode if models are not available.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    speaker: str
    text: str
    start: float = 0.0
    end: float = 0.0
    confidence: float = 1.0


@dataclass
class Transcript:
    language: str
    segments: List[TranscriptSegment] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(segment.text for segment in self.segments)


class WhisperService:
    """Whisper-based transcription service.
    
    Supports:
    - faster-whisper (recommended, faster and more efficient)
    - openai-whisper (fallback)
    - Stub mode (for testing without models)
    """
    
    def __init__(self, model_size: str = "large-v3", use_faster_whisper: bool = True):
        self.model_size = model_size
        self.use_faster_whisper = use_faster_whisper
        self.model = None
        self.processor = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize Whisper model."""
        try:
            if self.use_faster_whisper:
                try:
                    from faster_whisper import WhisperModel
                    logger.info(f"Loading faster-whisper model: {self.model_size}")
                    # Use GPU if available, fallback to CPU
                    device = "cuda" if self._check_cuda() else "cpu"
                    compute_type = "float16" if device == "cuda" else "int8"
                    self.model = WhisperModel(
                        self.model_size,
                        device=device,
                        compute_type=compute_type,
                        download_root=os.getenv("WHISPER_MODEL_CACHE", None)
                    )
                    logger.info(f"faster-whisper loaded on {device}")
                    return
                except ImportError:
                    logger.warning("faster-whisper not available, trying openai-whisper")
                    self.use_faster_whisper = False
            
            # Fallback to openai-whisper
            try:
                import whisper
                logger.info(f"Loading OpenAI Whisper model: {self.model_size}")
                self.model = whisper.load_model(self.model_size)
                logger.info("OpenAI Whisper loaded")
                return
            except ImportError:
                logger.warning("OpenAI Whisper not available, using stub mode")
                self.model = None
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}", exc_info=True)
            self.model = None
    
    def _check_cuda(self) -> bool:
        """Check if CUDA is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def transcribe(self, content: str | bytes, language: str = "fa", audio_path: Optional[str] = None) -> Transcript:
        """
        Transcribe audio content.
        
        Args:
            content: Text (for stub mode) or audio bytes
            language: Language code (default: "fa" for Farsi)
            audio_path: Optional path to audio file
            
        Returns:
            Transcript with segments
        """
        # If we have a real model, use it
        if self.model is not None:
            return self._transcribe_with_model(content, language, audio_path)
        
        # Stub mode for testing
        return self._transcribe_stub(content, language)
    
    def _transcribe_with_model(self, content: str | bytes, language: str, audio_path: Optional[str]) -> Transcript:
        """Transcribe using actual Whisper model."""
        try:
            if audio_path and os.path.exists(audio_path):
                # Transcribe from file
                if self.use_faster_whisper:
                    segments, info = self.model.transcribe(
                        audio_path,
                        language=language,
                        beam_size=5,
                        vad_filter=True,  # Use built-in VAD
                        vad_parameters=dict(min_silence_duration_ms=500)
                    )
                    transcript_segments = []
                    for segment in segments:
                        transcript_segments.append(TranscriptSegment(
                            speaker="unknown",
                            text=segment.text.strip(),
                            start=segment.start,
                            end=segment.end,
                            confidence=getattr(segment, 'avg_logprob', 0.0)
                        ))
                    return Transcript(language=info.language or language, segments=transcript_segments)
                else:
                    # OpenAI Whisper
                    result = self.model.transcribe(audio_path, language=language)
                    segments = []
                    for seg in result["segments"]:
                        segments.append(TranscriptSegment(
                            speaker="unknown",
                            text=seg["text"].strip(),
                            start=seg["start"],
                            end=seg["end"],
                            confidence=seg.get("no_speech_prob", 1.0)
                        ))
                    return Transcript(language=result.get("language", language), segments=segments)
            elif isinstance(content, bytes):
                # Transcribe from bytes (save to temp file first)
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                try:
                    return self._transcribe_with_model(None, language, tmp_path)
                finally:
                    os.unlink(tmp_path)
            else:
                # Text input (fallback to stub)
                return self._transcribe_stub(content, language)
        except Exception as e:
            logger.error(f"Error in transcription: {e}", exc_info=True)
            # Fallback to stub on error
            return self._transcribe_stub(content if isinstance(content, str) else "", language)
    
    def _transcribe_stub(self, content: str, language: str) -> Transcript:
        """Stub transcription for testing."""
        normalized = content.strip() if isinstance(content, str) else ""
        segments = [TranscriptSegment(speaker="unknown", text=normalized, start=0.0, end=1.0)] if normalized else []
        return Transcript(language=language, segments=segments)
    
    def transcribe_audio_file(self, audio_path: str, language: str = "fa") -> Transcript:
        """Convenience method to transcribe an audio file."""
        return self.transcribe("", language=language, audio_path=audio_path)
