import logging
import requests
import time
import os
import json
import hashlib
from typing import Dict, Any, List
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

class LLMEnricher:
    """
    Enriches and refines the structured document using DeepSeek-R1 8B via Ollama
    with performance optimizations, including topic detection and connection analysis.
    """

    def __init__(self, skip_enrichment: bool = False, max_content_length: int = 2000):
        self.model = "deepseek-r1:8b"
        self.api_url = "http://localhost:11434/api/chat"
        self.skip_enrichment = skip_enrichment
        self.max_content_length = max_content_length
        self.cache_dir = os.path.join(os.path.dirname(__file__), "cache", "llm")
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"LLMEnricher initialized with model: {self.model}")
        if self.skip_enrichment:
            logger.info("Enrichment is disabled - will use original content only")

        # Setup requests session with retries
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

    def enrich_document(self, structured_data: Any) -> Dict:
        """
        Refines the structured document with enhanced headings, content, topics, and connections.
        """
        start_time = time.time()
        logger.info(f"Enriching document with {self.model}...")
        self._check_ollama_status()
        logger.info(f"Input data type: {type(structured_data).__name__}")

        # Convert list to dictionary if needed
        if isinstance(structured_data, list):
            logger.info(f"Converting list of {len(structured_data)} items to dictionary format")
            converted_data = {"title": "Document", "sections": []}
            for item in structured_data:
                if isinstance(item, dict) and item.get("type") == "title":
                    converted_data["title"] = item.get("text", "Document")
                    break
            section_count = 0
            for item in structured_data:
                if isinstance(item, dict) and item.get("text") and len(item.get("text", "").strip()) > 10:
                    section = {"heading": item.get("type", "Section"), "content": item.get("text", ""), "subsections": []}
                    converted_data["sections"].append(section)
                    section_count += 1
            logger.info(f"Created {section_count} sections from list items")
            structured_data = converted_data

        logger.info(f"Processing document with title: '{structured_data.get('title', 'Untitled')}'")
        logger.info(f"Number of sections to process: {len(structured_data.get('sections', []))}")
        self._save_document(structured_data, "original_document.json")

        if self.skip_enrichment:
            logger.info("Skipping enrichment as requested")
            return structured_data

        # Process sections for topics and subsections
        all_topics = []
        for i, section in enumerate(structured_data.get("sections", [])):
            logger.info(f"Processing section {i + 1}: '{section.get('heading', 'Untitled Section')}'")
            if section.get("content") and not section.get("subsections"):
                # Split content into subsections
                content_chunks = self._chunk_content(section["content"])
                section["subsections"] = [
                    {"heading": f"Part {j + 1}", "content": chunk, "subsections": [], "topics": []}
                    for j, chunk in enumerate(content_chunks)
                ]
                section["content"] = ""
            for j, subsection in enumerate(section.get("subsections", [])):
                if subsection.get("content"):
                    topics = self.detect_topics(subsection["content"])
                    subsection["topics"] = topics
                    all_topics.extend(topics)

        # Find connections between topics
        connections = self.find_topic_connections(all_topics)
        structured_data["topic_connections"] = connections

        # Enrich title and sections
        if structured_data.get("title"):
            logger.info(f"Enriching document title: '{structured_data.get('title')}'")
            structured_data["title"] = self._enrich_title(structured_data.get("title"))
        for i, section in enumerate(structured_data.get("sections", [])):
            logger.info(f"Enriching section {i + 1}/{len(structured_data.get('sections', []))}")
            enriched_section = self._enrich_section(section)
            section.update(enriched_section)

        logger.info(f"Document enrichment completed in {time.time() - start_time:.2f} seconds")
        self._save_document(structured_data, "enriched_document.json")
        return structured_data

    def _chunk_content(self, content: str, chunk_size: int = 500) -> List[str]:
        """Split content into smaller chunks for topic detection."""
        words = content.split()
        chunks = []
        current_chunk = []
        current_length = 0
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            if current_length >= chunk_size:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks if chunks else [content]

    def detect_topics(self, content: str) -> List[Dict]:
        """Use Ollama to detect topics in content."""
        content = content[:self.max_content_length]
        prompt = f"""
        Analyze the following text and identify up to 3 distinct topics or themes.
        Return a JSON list of objects with keys: title (max 50 chars), summary (max 100 chars), text (max 200 chars).
        If no topics are identified, return an empty list.
        Text: {content}
        """
        cached = self._get_from_cache(prompt, "topics")
        if cached:
            try:
                return json.loads(cached)
            except Exception as e:
                logger.warning(f"Failed to parse cached topics: {e}")

        response = self._call_llm(prompt)
        try:
            topics = json.loads(response) if response else []
            if not isinstance(topics, list):
                logger.warning(f"Invalid topics format: {response}")
                topics = []
            self._save_to_cache(prompt, json.dumps(topics), "topics")
            logger.info(f"Detected {len(topics)} topics")
            return topics
        except Exception as e:
            logger.error(f"Failed to parse topics: {e}, response: {response}")
            return []

    def find_topic_connections(self, topics: List[Dict]) -> List[Dict]:
        """Use Ollama to find connections between topics."""
        if not topics or len(topics) < 2:
            logger.info("Not enough topics to find connections")
            return []

        topic_descriptions = "\n".join([f"{t['title']}: {t['summary']}" for t in topics])
        prompt = f"""
        Identify up to 3 connections between the following topics.
        Return a JSON list of objects with keys: topic1, topic2, connection (max 100 chars).
        If no connections are found, return an empty list.
        Topics:
        {topic_descriptions}
        """
        cached = self._get_from_cache(prompt, "connections")
        if cached:
            try:
                return json.loads(cached)
            except Exception as e:
                logger.warning(f"Failed to parse cached connections: {e}")

        response = self._call_llm(prompt)
        try:
            connections = json.loads(response) if response else []
            if not isinstance(connections, list):
                logger.warning(f"Invalid connections format: {response}")
                connections = []
            self._save_to_cache(prompt, json.dumps(connections), "connections")
            logger.info(f"Found {len(connections)} topic connections")
            return connections
        except Exception as e:
            logger.error(f"Failed to parse connections: {e}, response: {response}")
            return []

    def _save_document(self, document: Dict, filename: str) -> None:
        """Save document to a file."""
        try:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(document, f, indent=2)
            logger.info(f"Document saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save document: {e}")

    def _check_ollama_status(self) -> None:
        """Check if Ollama is running and the model is available."""
        try:
            response = self.session.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                if self.model in model_names or self.model.split(":")[0] in model_names:
                    logger.info(f"Ollama is running with model {self.model} available")
                else:
                    logger.warning(f"Model {self.model} not found. Available: {', '.join(model_names)}")
            else:
                logger.warning(f"Ollama API returned status code {response.status_code}")
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {str(e)}")

    def _enrich_section(self, section: Dict) -> Dict:
        """Enrich a section with LLM-based improvements."""
        enriched_section = section.copy()

        if section.get("heading"):
            logger.debug(f"Enriching heading: '{section.get('heading')}'")
            enriched_section["heading"] = self._enrich_heading(section["heading"])
            logger.debug(f"Enriched heading: '{enriched_section['heading']}'")

        if section.get("content") and len(section.get("content", "").strip()) > 20:
            content_preview = (
                section.get("content", "")[:50] + "..."
                if len(section.get("content", "")) > 50
                else section.get("content", "")
            )
            logger.debug(f"Enriching content: '{content_preview}'")
            enriched_section["content"] = self._enrich_content(section.get("content", ""))
            enriched_content_preview = (
                enriched_section.get("content", "")[:50] + "..."
                if len(enriched_section.get("content", "")) > 50
                else enriched_section.get("content", "")
            )
            logger.debug(f"Enriched content: '{enriched_content_preview}'")

        if section.get("subsections"):
            logger.debug(f"Enriching {len(section.get('subsections', []))} subsections")
            enriched_section["subsections"] = [
                self._enrich_section(sub) for sub in section.get("subsections", [])
            ]

        return enriched_section

    def _get_cache_key(self, text: str, prefix: str) -> str:
        """Generate a cache key for the given text."""
        hash_obj = hashlib.md5(text.encode("utf-8"))
        return f"{prefix}_{hash_obj.hexdigest()}"

    def _get_from_cache(self, text: str, prefix: str) -> str | None:
        """Get cached response if available."""
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

    def _save_to_cache(self, text: str, response: str, prefix: str) -> None:
        """Save response to cache."""
        cache_key = self._get_cache_key(text, prefix)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.txt")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(response)
            logger.debug(f"Cached response for {prefix}")
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    def _enrich_title(self, title: str) -> str:
        """Enrich the title with better clarity."""
        cached = self._get_from_cache(title, "title")
        if cached:
            return cached
        prompt = f"""
        Provide a concise, clear version of the document title (max 100 characters): {title}
        Return only the enriched title, without explanations or additional text.
        """
        result = self._call_llm(prompt) or title
        result = result.strip()[:100]  # Ensure concise output
        logger.debug(f"Title enrichment: '{title}' -> '{result}'")
        self._save_to_cache(title, result, "title")
        return result

    def _enrich_heading(self, heading: str) -> str:
        """Enrich a section heading."""
        cached = self._get_from_cache(heading, "heading")
        if cached:
            return cached
        prompt = f"""
        Provide a concise, enhanced version of the section heading (max 50 characters): {heading}
        Return only the enriched heading, without explanations or additional text.
        """
        result = self._call_llm(prompt) or heading
        result = result.strip()[:50]  # Ensure concise output
        logger.debug(f"Heading enrichment: '{heading}' -> '{result}'")
        self._save_to_cache(heading, result, "heading")
        return result

    def _enrich_content(self, content: str) -> str:
        """Enrich the content of a section/subsection."""
        cached = self._get_from_cache(content[:100], "content")
        if cached:
            return cached
        prompt = f"""
        Improve the following content for clarity and depth, keeping it concise (max 500 characters):
        {content[:self.max_content_length]}
        Return only the enriched content, without explanations or additional text.
        """
        result = self._call_llm(prompt) or content
        result = result.strip()[:500]  # Ensure concise output
        self._save_to_cache(content[:100], result, "content")
        return result

    def _call_llm(self, prompt: str) -> str:
        """Call the DeepSeek-R1 8B model via Ollama API with retry logic."""
        start_time = time.time()
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
            logger.debug(f"Sending request to Ollama API with prompt length: {len(prompt)} characters")
            response = self.session.post(self.api_url, json=payload, timeout=120)  # Increased timeout
            if response.status_code == 200:
                result = response.json()
                content = result.get("message", {}).get("content", "").strip()
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                logger.debug(f"LLM response received in {time.time() - start_time:.2f} seconds, length: {len(content)} characters")
                return content
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            logger.error(f"LLM API Error: {str(e)}")
            return ""