import requests
import logging
from typing import Dict, Deque
from collections import deque

logger = logging.getLogger(__name__)


class HURIDOCSParser:
    def __init__(self, docker_host="http://localhost:5060"):
        self.endpoint = f"{docker_host}/v1/segment"

    def parse_pdf(self, file_path: str) -> Dict:
        """Get structured content from HURIDOCS service"""
        try:
            with open(file_path, "rb") as f:
                response = requests.post(
                    self.endpoint,
                    files={"file": f},
                    headers={"Accept": "application/json"},
                    timeout=60,
                )
            return self._structure_response(response.json())
        except Exception as e:
            logger.error(f"HURIDOCS API Error: {str(e)}")
            return {"title": "", "sections": []}

    def _structure_response(self, data: Dict) -> Dict:
        """Convert HURIDOCS output to academic hierarchy"""
        structure = {"title": "", "sections": [], "_current_path": deque()}

        for segment in data.get("segments", []):
            self._process_segment(segment, structure)

        del structure["_current_path"]
        return structure

    def _process_segment(self, segment: Dict, structure: Dict):
        """Handle different academic elements"""
        seg_type = segment.get("type", "")
        text = segment.get("text", "").strip()

        if seg_type == "Title":
            structure["title"] = text
        elif seg_type == "Section header":
            self._add_section(text, segment, structure)
        elif seg_type == "Text":
            self._add_text(text, structure)
        elif seg_type == "Formula":
            self._add_formula(text, structure)
        elif seg_type == "Table":
            self._add_table(text, structure)

    def _add_section(self, text: str, segment: Dict, structure: Dict):
        """Add academic section with level detection"""
        level = self._calculate_level(segment)
        node = {
            "heading": text,
            "level": level,
            "content": "",
            "subsections": [],
            "type": "section",
        }

        # Hierarchy management
        while (
            structure["_current_path"]
            and structure["_current_path"][-1]["level"] >= level
        ):
            structure["_current_path"].pop()

        if structure["_current_path"]:
            structure["_current_path"][-1]["subsections"].append(node)
        else:
            structure["sections"].append(node)

        structure["_current_path"].append(node)

    def _calculate_level(self, segment: Dict) -> int:
        """Determine section level from layout position"""
        page_height = segment.get("page_height", 792)
        return 1 if segment.get("top", 0) < page_height * 0.2 else 2
