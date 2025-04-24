# semantic_extractor.py
from groq import Groq
import os
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class AcademicAnalyzer:
    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def analyze_content(self, content: str) -> Dict:
        """Enhanced academic analysis with concept linking"""
        try:
            # First pass: Core summary
            summary = self._get_summary(content)

            # Second pass: Concept relationships
            relationships = self._get_relationships(content)

            return {
                "summary": summary,
                "relationships": relationships,
                "keywords": self._extract_keywords(content),
            }
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return {"summary": "", "relationships": [], "keywords": []}

    def _get_summary(self, text: str) -> str:
        """Get academic-quality summary"""
        response = self.groq.chat.completions.create(
            model="llama3-70b",
            messages=[
                {
                    "role": "user",
                    "content": f"Summarize this academic content focusing on key contributions and methodology:\n{text}",
                }
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content

    def _get_relationships(self, text: str) -> List[Tuple]:
        """Extract concept relationships"""
        response = self.groq.chat.completions.create(
            model="llama3-70b",
            messages=[
                {
                    "role": "user",
                    "content": f"Identify conceptual relationships in this academic text. Format as 'concept1 -> concept2: relationship':\n{text}",
                }
            ],
            temperature=0.4,
        )
        return self._parse_relationships(response.choices[0].message.content)

    def _parse_relationships(self, text: str) -> List[Tuple]:
        """Parse LLM relationship response"""
        relationships = []
        for line in text.split("\n"):
            if "->" in line:
                parts = line.split("->")
                if len(parts) == 2:
                    source = parts[0].strip()
                    target_part = parts[1].split(":")
                    target = target_part[0].strip()
                    relation = (
                        target_part[1].strip() if len(target_part) > 1 else "related"
                    )
                    relationships.append((source, target, relation))
        return relationships
