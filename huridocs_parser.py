import json
import os
import re  # Missing import for regex
import logging
import requests
from typing import List, Dict, Any
import hashlib
# import shelve # more robust but should i?

# Setting up logging
logger = logging.getLogger(__name__)


def get_file_hash(file_path: str) -> str:
    """Generate a unique hash for a file based on its content and path"""
    file_hash = hashlib.md5()
    file_hash.update(file_path.encode("utf-8"))

    # Also include file modification time for cache invalidation
    file_hash.update(str(os.path.getmtime(file_path)).encode("utf-8"))

    return file_hash.hexdigest()


class HURIDOCSParser:
    """
    Parses HURIDOCS SegmentBox JSON-like structure into a hierarchical document tree
    """

    def __init__(self):
        self.title = None
        self.structure = {"title": None, "sections": []}

    def parse_pdf(self, segments: List[Dict[str, Any]]) -> Dict:
        # Sort segments by page and then top position (vertical)
        segments.sort(key=lambda x: (x["page_number"], x["top"]))

        current_section = None
        current_subsection = None

        for segment in segments:
            text = segment.get("text", "").strip()
            segment_type = segment.get("type", "")
            top = segment.get("top", 0)

            if not text or len(text) < 2:
                continue  # skip empty or trivial lines

            # Detect document title (first large top-level title)
            if not self.structure["title"] and segment_type.lower() == "title":
                self.structure["title"] = text
                continue

            # Detect headings using basic regex + heuristics
            if self._is_heading(text):
                if self._is_subheading(text):
                    current_subsection = {
                        "heading": text,
                        "content": "",
                    }
                    if current_section:
                        current_section.setdefault("subsections", []).append(
                            current_subsection
                        )
                else:
                    current_section = {
                        "heading": text,
                        "content": "",
                        "subsections": [],
                    }
                    self.structure["sections"].append(current_section)
                    current_subsection = None

            else:
                # Treat as content
                if current_subsection:
                    current_subsection["content"] += text + " "
                elif current_section:
                    current_section["content"] += text + " "

        return self.structure

    def _is_heading(self, text: str) -> bool:
        """Detects if a line is likely a heading (e.g., numbered or title-case)"""
        return bool(re.match(r"^\d+(\.\d+)*\s+.+", text)) or text.istitle()

    def _is_subheading(self, text: str) -> bool:
        """Detects if heading is a subsection (e.g., 1.1, 2.3.1, etc.)"""
        return bool(re.match(r"^\d+\.\d+(\.\d+)*\s+.+", text))


def parse_pdf_with_huridocs(pdf_path: str) -> Dict[str, Any]:
    """Parse PDF with HURIDOCS with caching support"""
    # Check if the file exists
    if not os.path.exists(pdf_path):
        logger.error(f"File not found: {pdf_path}")
        return {}

    # Create cache directory if it doesn't exist
    cache_dir = os.path.join(os.path.dirname(__file__), "cache")
    os.makedirs(cache_dir, exist_ok=True)

    # Generate a unique hash for this PDF file
    file_hash = get_file_hash(pdf_path)
    cache_file = os.path.join(cache_dir, f"{file_hash}.json")

    # Check if we have a cached version
    if os.path.exists(cache_file):
        logger.info(f"Loading cached parse results for {pdf_path}")
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}. Will parse PDF again.")

    # If no cache or cache loading failed, parse the PDF
    logger.info(f"Sending PDF {pdf_path} for parsing...")

    # Connect to local HURIDOCS Docker container
    api_url = "http://localhost:5060"

    try:
        with open(pdf_path, "rb") as pdf_file:
            files = {"file": (os.path.basename(pdf_path), pdf_file, "application/pdf")}
            response = requests.post(api_url, files=files)

            if response.status_code == 200:
                segments = response.json()
                logger.info(f"Successfully parsed PDF with {len(segments)} segments")

                # Cache the results
                try:
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(segments, f)
                    logger.info(f"Cached parse results to {cache_file}")
                except Exception as e:
                    logger.warning(f"Failed to cache results: {e}")

                # Process the segments
                parser = HURIDOCSParser()
                return parser.parse_pdf(segments)
            else:
                logger.error(
                    f"API returned error: {response.status_code} - {response.text}"
                )
                return {}
    except Exception as e:
        logger.error(f"Failed to connect to HURIDOCS service: {str(e)}")
        return {}


def parse_segments(segments):
    """Parse the segments returned by HURIDOCS into a structured document"""
    parser = HURIDOCSParser()
    return parser.parse_pdf(segments)
