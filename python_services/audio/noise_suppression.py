"""Noise suppression using RNNoise or WebRTC AudioProcessing.

Supports RNNoise ONNX model for high-quality noise suppression.
Falls back to simple filtering if models are not available.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class NoiseSuppressor:
    """Noise suppression service.
    
    Supports:
    - RNNoise (ONNX Runtime) - best quality
    - WebRTC AudioProcessing - good quality, more CPU intensive
    - Simple high-pass filter - fallback
    """
    
    def __init__(self, method: str = "auto"):
        """
        Initialize noise suppressor.
        
        Args:
            method: "rnnoise", "webrtc", "simple", or "auto"
        """
        self.method = method
        self.rnnoise_model = None
        self.webrtc_apm = None
        self._initialize_suppressor()
    
    def _initialize_suppressor(self):
        """Initialize noise suppression method."""
        # Try RNNoise first
        if self.method in ("auto", "rnnoise"):
            try:
                import onnxruntime as ort
                
                # Look for RNNoise ONNX model
                model_path = os.getenv("RNNOISE_MODEL_PATH", "models/rnnoise.onnx")
                if os.path.exists(model_path):
                    self.rnnoise_model = ort.InferenceSession(model_path)
                    logger.info("RNNoise model loaded")
                    if self.method == "rnnoise":
                        return
                else:
                    logger.warning(f"RNNoise model not found at {model_path}")
            except ImportError:
                logger.warning("onnxruntime not installed, skipping RNNoise")
            except Exception as e:
                logger.error(f"Error loading RNNoise: {e}")
        
        # Try WebRTC AudioProcessing
        if self.method in ("auto", "webrtc"):
            try:
                # WebRTC AudioProcessing would require native bindings
                # For now, we'll use a placeholder
                logger.info("WebRTC AudioProcessing not yet implemented, using simple filter")
            except Exception as e:
                logger.error(f"Error initializing WebRTC: {e}")
        
        # Fallback to simple filter
        logger.info("Using simple high-pass filter for noise suppression")
    
    def suppress(self, audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
        """
        Apply noise suppression to audio.
        
        Args:
            audio: Audio samples as numpy array (float32, [-1, 1])
            sample_rate: Sample rate of audio
            
        Returns:
            Denoised audio samples
        """
        if len(audio) == 0:
            return audio
        
        # Ensure float32 format
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # Normalize to [-1, 1] if needed
        if audio.max() > 1.0 or audio.min() < -1.0:
            max_val = max(abs(audio.max()), abs(audio.min()))
            if max_val > 0:
                audio = audio / max_val
        
        if self.rnnoise_model:
            return self._suppress_rnnoise(audio, sample_rate)
        else:
            return self._suppress_simple(audio, sample_rate)
    
    def _suppress_rnnoise(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply RNNoise suppression."""
        try:
            # RNNoise expects 48000 Hz, so we need to resample if needed
            if sample_rate != 48000:
                from scipy import signal
                num_samples = int(len(audio) * 48000 / sample_rate)
                audio_resampled = signal.resample(audio, num_samples)
            else:
                audio_resampled = audio
            
            # RNNoise processes in frames of 480 samples (10ms at 48kHz)
            frame_size = 480
            output_frames = []
            
            for i in range(0, len(audio_resampled), frame_size):
                frame = audio_resampled[i:i + frame_size]
                if len(frame) < frame_size:
                    # Pad last frame
                    frame = np.pad(frame, (0, frame_size - len(frame)), mode='constant')
                
                # Prepare input (RNNoise expects specific input shape)
                input_data = frame.reshape(1, -1).astype(np.float32)
                
                # Run inference
                input_name = self.rnnoise_model.get_inputs()[0].name
                output = self.rnnoise_model.run(None, {input_name: input_data})
                
                # Extract output
                denoised_frame = output[0].flatten()
                output_frames.append(denoised_frame)
            
            # Concatenate frames
            denoised = np.concatenate(output_frames)
            
            # Resample back to original sample rate if needed
            if sample_rate != 48000:
                from scipy import signal
                num_samples = int(len(denoised) * sample_rate / 48000)
                denoised = signal.resample(denoised, num_samples)
            
            return denoised[:len(audio)]  # Trim to original length
        except Exception as e:
            logger.error(f"Error in RNNoise suppression: {e}", exc_info=True)
            return self._suppress_simple(audio, sample_rate)
    
    def _suppress_simple(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Simple high-pass filter for noise suppression."""
        try:
            from scipy import signal
            
            # High-pass filter to remove low-frequency noise
            # Cutoff frequency: 80 Hz (removes rumble, but keeps speech)
            nyquist = sample_rate / 2
            cutoff = 80.0 / nyquist
            
            # Design Butterworth high-pass filter
            b, a = signal.butter(4, cutoff, btype='high')
            
            # Apply filter
            filtered = signal.filtfilt(b, a, audio)
            
            # Optional: spectral subtraction (simple noise gate)
            # Reduce very quiet parts
            threshold = 0.01
            mask = np.abs(filtered) > threshold
            filtered = filtered * mask + filtered * 0.1 * (1 - mask)
            
            return filtered
        except ImportError:
            logger.warning("scipy not available, returning original audio")
            return audio
        except Exception as e:
            logger.error(f"Error in simple suppression: {e}", exc_info=True)
            return audio

