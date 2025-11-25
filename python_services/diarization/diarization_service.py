"""Speaker diarization service using pyannote.audio.

Supports pyannote.audio 3.1 for high-quality speaker diarization.
Falls back to simple hash-based clustering if models are not available.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

from python_services.stt.whisper_service import Transcript, TranscriptSegment

logger = logging.getLogger(__name__)


@dataclass
class DiarizedSegment:
    speaker: str
    text: str
    start: float = 0.0
    end: float = 0.0
    confidence: float = 1.0


class DiarizationService:
    """Speaker diarization service.
    
    Uses pyannote.audio for production-quality diarization.
    Falls back to simple text-based hashing if models unavailable.
    """
    
    def __init__(self, use_pyannote: bool = True):
        self.use_pyannote = use_pyannote
        self.diarization_pipeline = None
        self.embedding_model = None
        self.speaker_embeddings: Dict[str, List] = {}  # speaker_id -> list of embeddings
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize pyannote.audio models."""
        if not self.use_pyannote:
            logger.info("Diarization: Using simple hash-based mode")
            return
        
        try:
            from pyannote.audio import Pipeline
            from pyannote.core import Annotation
            
            # Check for HuggingFace token
            hf_token = os.getenv("HUGGINGFACE_TOKEN")
            if not hf_token:
                logger.warning("HUGGINGFACE_TOKEN not set, diarization will use fallback mode")
                self.use_pyannote = False
                return
            
            logger.info("Loading pyannote.audio diarization pipeline...")
            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token
            )
            
            # Try to load embedding model for speaker identification
            try:
                from pyannote.audio import Model
                self.embedding_model = Model.from_pretrained(
                    "pyannote/embedding",
                    use_auth_token=hf_token
                )
                logger.info("Speaker embedding model loaded")
            except Exception as e:
                logger.warning(f"Could not load embedding model: {e}")
                self.embedding_model = None
            
            logger.info("pyannote.audio diarization pipeline loaded successfully")
        except ImportError:
            logger.warning("pyannote.audio not available, using fallback mode")
            self.use_pyannote = False
        except Exception as e:
            logger.error(f"Error loading pyannote.audio: {e}", exc_info=True)
            self.use_pyannote = False
    
    def diarize(self, transcript: Transcript, audio_path: Optional[str] = None) -> List[DiarizedSegment]:
        """
        Perform speaker diarization on transcript.
        
        Args:
            transcript: Transcript with segments
            audio_path: Optional path to audio file for diarization
            
        Returns:
            List of diarized segments with speaker labels
        """
        if self.use_pyannote and audio_path and os.path.exists(audio_path):
            return self._diarize_with_pyannote(transcript, audio_path)
        
        # Fallback to simple text-based clustering
        return self._diarize_simple(transcript)
    
    def _diarize_with_pyannote(self, transcript: Transcript, audio_path: str) -> List[DiarizedSegment]:
        """Diarize using pyannote.audio."""
        try:
            # Run diarization pipeline
            diarization = self.diarization_pipeline(audio_path)
            
            # Map transcript segments to diarization results
            diarized_segments = []
            
            for seg in transcript.segments:
                # Find overlapping diarization segments
                speaker = self._find_speaker_for_segment(seg.start, seg.end, diarization)
                
                diarized_segments.append(DiarizedSegment(
                    speaker=speaker,
                    text=seg.text,
                    start=seg.start,
                    end=seg.end,
                    confidence=seg.confidence
                ))
            
            return diarized_segments
        except Exception as e:
            logger.error(f"Error in pyannote diarization: {e}", exc_info=True)
            return self._diarize_simple(transcript)
    
    def _find_speaker_for_segment(self, start: float, end: float, diarization) -> str:
        """Find the dominant speaker for a time segment."""
        # Get all speakers active during this segment
        speakers_in_segment = {}
        
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            # Check overlap
            overlap_start = max(start, turn.start)
            overlap_end = min(end, turn.end)
            
            if overlap_start < overlap_end:
                duration = overlap_end - overlap_start
                if speaker not in speakers_in_segment:
                    speakers_in_segment[speaker] = 0.0
                speakers_in_segment[speaker] += duration
        
        if not speakers_in_segment:
            return "unknown"
        
        # Return speaker with most overlap
        dominant_speaker = max(speakers_in_segment.items(), key=lambda x: x[1])[0]
        return dominant_speaker
    
    def _diarize_simple(self, transcript: Transcript) -> List[DiarizedSegment]:
        """Simple hash-based diarization fallback."""
        diarized: List[DiarizedSegment] = []
        for segment in transcript.segments:
            speaker = self._hash_speaker(segment.text) if segment.text else "unknown"
            diarized.append(DiarizedSegment(
                speaker=speaker,
                text=segment.text,
                start=segment.start,
                end=segment.end,
                confidence=segment.confidence
            ))
        return diarized
    
    def _hash_speaker(self, text: str) -> str:
        """Generate speaker ID from text hash."""
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"speaker-{digest[:8]}"
    
    def identify_speaker(self, audio_chunk: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        Identify speaker from audio chunk using embedding similarity.
        
        Args:
            audio_chunk: Audio bytes
            sample_rate: Sample rate of audio
            
        Returns:
            Speaker ID if found, None if unknown
        """
        if not self.embedding_model:
            return None
        
        try:
            # Extract embedding from audio chunk
            # This is a simplified version - real implementation would need
            # proper audio preprocessing and embedding extraction
            embedding = self._extract_embedding(audio_chunk, sample_rate)
            
            if embedding is None:
                return None
            
            # Compare with stored embeddings
            best_match = None
            best_similarity = 0.0
            threshold = 0.7  # Similarity threshold
            
            for speaker_id, stored_embeddings in self.speaker_embeddings.items():
                for stored_emb in stored_embeddings:
                    similarity = self._cosine_similarity(embedding, stored_emb)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = speaker_id
            
            if best_similarity >= threshold:
                return best_match
            
            return None
        except Exception as e:
            logger.error(f"Error identifying speaker: {e}", exc_info=True)
            return None
    
    def enroll_speaker(self, speaker_id: str, audio_chunk: bytes, sample_rate: int = 16000):
        """Enroll a new speaker or update existing speaker profile."""
        if not self.embedding_model:
            return
        
        try:
            embedding = self._extract_embedding(audio_chunk, sample_rate)
            if embedding is not None:
                if speaker_id not in self.speaker_embeddings:
                    self.speaker_embeddings[speaker_id] = []
                self.speaker_embeddings[speaker_id].append(embedding)
                # Keep only last 5 embeddings per speaker
                if len(self.speaker_embeddings[speaker_id]) > 5:
                    self.speaker_embeddings[speaker_id] = self.speaker_embeddings[speaker_id][-5:]
        except Exception as e:
            logger.error(f"Error enrolling speaker: {e}", exc_info=True)
    
    def _extract_embedding(self, audio_chunk: bytes, sample_rate: int):
        """Extract speaker embedding from audio chunk."""
        # This is a placeholder - real implementation would use pyannote embedding model
        # For now, return None to indicate not implemented
        return None
    
    def _cosine_similarity(self, a, b) -> float:
        """Calculate cosine similarity between two embeddings."""
        import numpy as np
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
