import logging
import requests
import time
import os
import json
import hashlib
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class LLMEnricher:
    """
    Enriches and refines the structured document using DeepSeek-R1 8B via Ollama
    with performance optimizations
    """

    def __init__(self, skip_enrichment=False):
        self.model = "deepseek-r1:8b"
        self.api_url = "http://localhost:11434/api/chat"
        self.skip_enrichment = skip_enrichment
        self.cache_dir = os.path.join(os.path.dirname(__file__), "cache", "llm")
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"LLMEnricher initialized with model: {self.model}")
        if self.skip_enrichment:
            logger.info("Enrichment is disabled - will use original content only")

    def enrich_document(self, structured_data: Any) -> Dict:
        """
        Refines the structured document with enhanced headings, content, and potential reordering
        using DeepSeek-R1 8B.
        """
        start_time = time.time()
        logger.info(f"Enriching document with {self.model}...")

        # Check if Ollama is running
        if not self.skip_enrichment:
            self._check_ollama_status()

        # Log the input data type
        logger.info(f"Input data type: {type(structured_data).__name__}")

        # Check if structured_data is a list and convert if needed
        if isinstance(structured_data, list):
            logger.info(
                f"Converting list of {len(structured_data)} items to dictionary format"
            )
            # Convert list to dictionary format
            converted_data = {
                "title": "Document",  # Default title
                "sections": [],
            }

            # Try to find a title in the segments
            for item in structured_data:
                if isinstance(item, dict) and item.get("type") == "title":
                    converted_data["title"] = item.get("text", "Document")
                    logger.info(f"Found document title: {converted_data['title']}")
                    break

            # Process each item in the list as a section
            section_count = 0
            for item in structured_data:
                if isinstance(item, dict):
                    # If the item has text and type, create a section
                    if item.get("text") and len(item.get("text", "").strip()) > 10:
                        section = {
                            "heading": item.get("type", "Section"),
                            "content": item.get("text", ""),
                            "subsections": [],
                        }
                        converted_data["sections"].append(section)
                        section_count += 1

            logger.info(f"Created {section_count} sections from list items")
            structured_data = converted_data

        # Now proceed with dictionary format
        logger.info(
            f"Processing document with title: '{structured_data.get('title', 'Untitled')}'"
        )
        logger.info(
            f"Number of sections to process: {len(structured_data.get('sections', []))}"
        )

        # Save original document before enrichment
        self._save_document(structured_data, "original_document.json")

        if self.skip_enrichment:
            logger.info("Skipping enrichment as requested")
            return structured_data

        # Loop through sections and enrich the content of each
        for i, section in enumerate(structured_data.get("sections", [])):
            logger.info(
                f"Enriching section {i + 1}/{len(structured_data.get('sections', []))}: '{section.get('heading', 'Untitled Section')}'"
            )
            start_section_time = time.time()
            enriched_section = self._enrich_section(section)
            section.update(enriched_section)
            logger.info(
                f"Section {i + 1} enriched in {time.time() - start_section_time:.2f} seconds"
            )

        # Enhance the title
        if structured_data.get("title"):
            logger.info(f"Enriching document title: '{structured_data.get('title')}'")
            start_title_time = time.time()
            title_enriched = self._enrich_title(structured_data.get("title"))
            structured_data["title"] = title_enriched
            logger.info(
                f"Title enriched in {time.time() - start_title_time:.2f} seconds"
            )

        logger.info(
            f"Document enrichment completed in {time.time() - start_time:.2f} seconds"
        )

        # Save enriched document
        self._save_document(structured_data, "enriched_document.json")

        return structured_data

    def _save_document(self, document, filename):
        """Save document to a file"""
        try:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(document, f, indent=2)
            logger.info(f"Document saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save document: {e}")

    def _check_ollama_status(self):
        """Check if Ollama is running and the model is available"""
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                if self.model in model_names or self.model.split(":")[0] in model_names:
                    logger.info(f"Ollama is running with model {self.model} available")
                else:
                    logger.warning(
                        f"Model {self.model} not found in Ollama. Available models: {', '.join(model_names)}"
                    )
            else:
                logger.warning(
                    f"Ollama API returned status code {response.status_code}"
                )
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {str(e)}")

    def _enrich_section(self, section: Dict) -> Dict:
        """Enrich a section with LLM-based improvements"""
        enriched_section = section.copy()

        # Enrich section heading
        if section.get("heading"):
            logger.debug(f"Enriching heading: '{section.get('heading')}'")
            section["heading"] = self._enrich_heading(section["heading"])
            logger.debug(f"Enriched heading: '{section.get('heading')}'")

        # Enrich content - only if it's substantial
        if section.get("content") and len(section.get("content", "").strip()) > 20:
            content_preview = (
                section.get("content", "")[:50] + "..."
                if len(section.get("content", "")) > 50
                else section.get("content", "")
            )
            logger.debug(f"Enriching content: '{content_preview}'")
            enriched_section["content"] = self._enrich_content(
                section.get("content", "")
            )
            enriched_content_preview = (
                enriched_section.get("content", "")[:50] + "..."
                if len(enriched_section.get("content", "")) > 50
                else enriched_section.get("content", "")
            )
            logger.debug(f"Enriched content: '{enriched_content_preview}'")

        # Enrich subsections recursively
        if section.get("subsections"):
            logger.debug(f"Enriching {len(section.get('subsections', []))} subsections")
            enriched_section["subsections"] = [
                self._enrich_section(sub) for sub in section.get("subsections", [])
            ]

        return enriched_section

    def _get_cache_key(self, text, prefix):
        """Generate a cache key for the given text"""
        hash_obj = hashlib.md5(text.encode("utf-8"))
        return f"{prefix}_{hash_obj.hexdigest()}"

    def _get_from_cache(self, text, prefix):
        """Get cached response if available"""
        cache_key = self._get_cache_key(text, prefix)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.txt")

        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_response = f.read()
                logger.debug(f"Using cached response for {prefix}")
                return cached_response
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")

        return None

    def _save_to_cache(self, text, response, prefix):
        """Save response to cache"""
        cache_key = self._get_cache_key(text, prefix)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.txt")

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(response)
            logger.debug(f"Cached response for {prefix}")
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    def _enrich_title(self, title: str) -> str:
        """Enrich the title (maybe rephrase, add additional keywords)"""
        # Check cache first
        cached = self._get_from_cache(title, "title")
        if cached:
            return cached

        prompt = f"Enrich the following document title for better clarity: {title}"
        result = self._call_llm(prompt) or title
        logger.debug(f"Title enrichment: '{title}' -> '{result}'")

        # Cache the result
        self._save_to_cache(title, result, "title")

        return result

    def _enrich_heading(self, heading: str) -> str:
        """Enrich a section heading"""
        # Check cache first
        cached = self._get_from_cache(heading, "heading")
        if cached:
            return cached

        prompt = (
            f"Enhance this section heading for better clarity and structure: {heading}"
        )
        result = self._call_llm(prompt) or heading
        logger.debug(f"Heading enrichment: '{heading}' -> '{result}'")

        # Cache the result
        self._save_to_cache(heading, result, "heading")

        return result

    def _enrich_content(self, content: str) -> str:
        """Enrich the content of a section/subsection"""
        # Check cache first
        cached = self._get_from_cache(
            content[:100], "content"
        )  # Use first 100 chars as key
        if cached:
            return cached

        prompt = f"Improve and expand upon the following content for clarity, detail, and depth: {content}"
        result = self._call_llm(prompt) or content

        # Cache the result
        self._save_to_cache(content[:100], result, "content")

        return result

    def _call_llm(self, prompt: str) -> str:
        """Call the DeepSeek-R1 8B model via Ollama API and return the response"""
        start_time = time.time()
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }

            logger.debug(
                f"Sending request to Ollama API with prompt length: {len(prompt)} characters"
            )
            response = requests.post(
                self.api_url, json=payload, timeout=60
            )  # Add timeout

            if response.status_code == 200:
                result = response.json()
                # Extract content from the response
                content = result.get("message", {}).get("content", "").strip()

                # Remove thinking process if present (enclosed in <think> tags)
                import re

                original_length = len(content)
                content = re.sub(
                    r"<think>.*?</think>", "", content, flags=re.DOTALL
                ).strip()
                if original_length != len(content):
                    logger.debug(
                        f"Removed thinking process ({original_length - len(content)} characters)"
                    )

                logger.debug(
                    f"LLM response received in {time.time() - start_time:.2f} seconds, length: {len(content)} characters"
                )
                return content
            else:
                logger.error(
                    f"Ollama API error: {response.status_code} - {response.text}"
                )
                return ""
        except Exception as e:
            logger.error(f"LLM API Error: {str(e)}")
            return ""
