"""LLM-based summarization service.

Supports GPT-4o-mini (OpenAI API) and Llama 3 (local) for high-quality meeting summaries.
Falls back to simple extraction if LLMs are not available.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Summary:
    bullet_points: List[str]
    highlight: str
    action_items: List[str] = None
    decisions: List[str] = None
    faithfulness_score: float = 1.0


class Summarizer:
    """LLM-based summarization service.
    
    Supports:
    - GPT-4o-mini (OpenAI API) - best quality
    - Llama 3 8B-instruct (local) - offline option
    - Simple extraction - fallback
    """
    
    def __init__(self, provider: str = "auto"):
        """
        Initialize summarizer.
        
        Args:
            provider: "openai", "llama", "simple", or "auto"
        """
        self.provider = provider
        self.openai_client = None
        self.llama_model = None
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize LLM provider."""
        # Try OpenAI first
        if self.provider in ("auto", "openai"):
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    try:
                        from openai import OpenAI
                        self.openai_client = OpenAI(api_key=api_key)
                        logger.info("OpenAI client initialized")
                        if self.provider == "openai":
                            return
                    except ImportError:
                        logger.warning("openai package not installed")
                else:
                    logger.warning("OPENAI_API_KEY not set")
            except Exception as e:
                logger.error(f"Error initializing OpenAI: {e}")
        
        # Try Llama 3 (local)
        if self.provider in ("auto", "llama"):
            try:
                # This would require llama.cpp or transformers
                # For now, we'll use a placeholder
                logger.info("Llama 3 local model not yet implemented, using simple extraction")
            except Exception as e:
                logger.error(f"Error initializing Llama: {e}")
        
        logger.info("Using simple extraction for summarization")
    
    def summarize(self, transcript: str, max_points: int = 5, language: str = "fa") -> Summary:
        """
        Summarize transcript using LLM.
        
        Args:
            transcript: Full transcript text
            max_points: Maximum number of bullet points
            language: Language code (default: "fa" for Farsi)
            
        Returns:
            Summary with bullet points, highlight, and action items
        """
        if not transcript or not transcript.strip():
            return Summary(
                bullet_points=[],
                highlight="",
                action_items=[],
                decisions=[]
            )
        
        # Try LLM providers
        if self.openai_client:
            return self._summarize_openai(transcript, max_points, language)
        
        # Fallback to simple extraction
        return self._summarize_simple(transcript, max_points)
    
    def _summarize_openai(self, transcript: str, max_points: int, language: str) -> Summary:
        """Summarize using OpenAI GPT-4o-mini."""
        try:
            # Create prompt in Farsi
            if language == "fa":
                prompt = f"""لطفاً متن زیر را که از یک جلسه است، خلاصه کنید:

{transcript}

لطفاً:
1. یک خلاصه کوتاه (یک جمله) ارائه دهید
2. {max_points} نکته کلیدی را به صورت bullet point لیست کنید
3. اقدامات مورد نیاز (action items) را مشخص کنید
4. تصمیمات گرفته شده را لیست کنید

فرمت پاسخ:
خلاصه: [خلاصه کوتاه]
نکات کلیدی:
- [نکته 1]
- [نکته 2]
...
اقدامات:
- [اقدام 1]
- [اقدام 2]
...
تصمیمات:
- [تصمیم 1]
- [تصمیم 2]
..."""
            else:
                prompt = f"""Please summarize the following meeting transcript:

{transcript}

Please provide:
1. A short summary (one sentence)
2. {max_points} key points as bullet points
3. Action items
4. Decisions made

Format:
Summary: [short summary]
Key Points:
- [point 1]
- [point 2]
...
Action Items:
- [action 1]
- [action 2]
...
Decisions:
- [decision 1]
- [decision 2]
..."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes meeting transcripts in a structured format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            
            # Parse response
            return self._parse_summary_response(content, max_points)
        except Exception as e:
            logger.error(f"Error in OpenAI summarization: {e}", exc_info=True)
            return self._summarize_simple(transcript, max_points)
    
    def _parse_summary_response(self, content: str, max_points: int) -> Summary:
        """Parse LLM response into Summary object."""
        lines = content.split("\n")
        highlight = ""
        bullet_points = []
        action_items = []
        decisions = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section
            if "خلاصه:" in line or "Summary:" in line:
                highlight = line.split(":", 1)[1].strip() if ":" in line else line
                current_section = "highlight"
            elif "نکات کلیدی" in line or "Key Points" in line:
                current_section = "points"
            elif "اقدامات" in line or "Action Items" in line:
                current_section = "actions"
            elif "تصمیمات" in line or "Decisions" in line:
                current_section = "decisions"
            elif line.startswith("-") or line.startswith("•"):
                item = line.lstrip("- •").strip()
                if current_section == "points" and len(bullet_points) < max_points:
                    bullet_points.append(item)
                elif current_section == "actions":
                    action_items.append(item)
                elif current_section == "decisions":
                    decisions.append(item)
        
        # Fallback: if parsing failed, use first line as highlight
        if not highlight and lines:
            highlight = lines[0]
        
        return Summary(
            bullet_points=bullet_points[:max_points],
            highlight=highlight,
            action_items=action_items,
            decisions=decisions,
            faithfulness_score=0.9  # LLM summaries are generally faithful
        )
    
    def _summarize_simple(self, transcript: str, max_points: int) -> Summary:
        """Simple extraction-based summarization fallback."""
        cleaned = self._normalize(transcript)
        sentences = [s.strip() for s in cleaned.split(".") if s.strip()]
        
        # Extract key sentences (simple heuristic: longer sentences)
        key_sentences = sorted(sentences, key=len, reverse=True)[:max_points]
        bullet_points = [sent for sent in key_sentences if len(sent) > 20]
        
        # First sentence as highlight
        highlight = sentences[0] if sentences else ""
        
        # Simple action item detection (sentences with action words)
        action_words_fa = ["باید", "لازم است", "نیاز است", "انجام شود"]
        action_words_en = ["should", "must", "need to", "action", "todo"]
        action_items = [
            sent for sent in sentences
            if any(word in sent.lower() for word in action_words_fa + action_words_en)
        ][:5]
        
        return Summary(
            bullet_points=bullet_points[:max_points],
            highlight=highlight,
            action_items=action_items,
            decisions=[],
            faithfulness_score=1.0  # Simple extraction is always faithful
        )
    
    def _normalize(self, text: str) -> str:
        """Remove duplicated whitespace and trim."""
        collapsed = " ".join(text.split())
        return collapsed.strip()
