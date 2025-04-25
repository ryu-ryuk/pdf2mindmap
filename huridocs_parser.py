import json
import os
import re
import logging
import requests
import hashlib
import subprocess
from typing import Dict, Any, List
from pathlib import Path
from lxml import etree
import pdfplumber

# Setting up logging
logger = logging.getLogger(__name__)


def get_file_hash(file_path: str) -> str:
    """Generate a unique hash for a file based on its content and path"""
    file_hash = hashlib.md5()
    file_hash.update(file_path.encode("utf-8"))

    # Also include file modification time for cache invalidation
    file_hash.update(str(os.path.getmtime(file_path)).encode("utf-8"))

    return file_hash.hexdigest()


class GrobidParser:
    """
    Parses PDFs using GROBID service and converts the TEI XML output
    into a hierarchical document structure
    """

    def __init__(self, grobid_url="http://localhost:8070"):
        self.grobid_url = grobid_url
        self.structure = {"title": None, "sections": []}

    def parse_pdf(self, pdf_path: str) -> Dict:
        """
        Process a PDF file with GROBID and extract structured content
        """
        # Call GROBID API to process the PDF
        tei_xml = self._process_pdf_with_grobid(pdf_path)
        if not tei_xml:
            logger.error("Failed to process PDF with GROBID")
            return self.structure

        # Parse the TEI XML to extract structured content
        return self._parse_tei_xml(tei_xml)
    def _process_pdf_with_grobid(self, pdf_path: str) -> str:
        try:
            url = f"{self.grobid_url}/api/processFulltextDocument"
            with open(pdf_path, "rb") as pdf_file:
                files = {"input": (os.path.basename(pdf_path), pdf_file, "application/pdf")}
                data = {"consolidateHeader": "1", "teiCoordinates": "1", "segmentSentences": "1"}
                response = requests.post(url, files=files, data=data)
                if response.status_code == 200:
                    logger.info(f"Successfully processed PDF with GROBID")
                    # Save TEI XML for debugging
                    with open("grobid_output.xml", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    return response.text
                else:
                    logger.error(f"GROBID API error: {response.status_code} - {response.text}")
                    return ""
        except Exception as e:
            logger.error(f"Error calling GROBID API: {str(e)}")
            return ""


    def _parse_tei_xml(self, tei_xml: str) -> Dict:
        try:
            structure = {"title": None, "sections": []}
            parser = etree.XMLParser(recover=True)  # Recover from malformed XML
            root = etree.fromstring(tei_xml.encode("utf-8"), parser)

            # Extract title
            title_elem = root.xpath("//tei:titleStmt/tei:title[@type='main']", namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
            structure["title"] = title_elem[0].text.strip() if title_elem and title_elem[0].text else " Untitled Document"

            # Extract sections
            for div in root.xpath("//tei:div", namespaces={"tei": "http://www.tei-c.org/ns/1.0"}):
                section = {"heading": None, "content": "", "subsections": []}
                
                # Get heading
                head = div.xpath(".//tei:head", namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
                section["heading"] = head[0].text.strip() if head and head[0].text else f"Section {len(structure['sections']) + 1}"
                
                # Get content (all paragraphs)
                paragraphs = div.xpath(".//tei:p", namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
                section["content"] = " ".join(p.text.strip() for p in paragraphs if p.text).strip()
                
                # Get subsections
                for sub_div in div.xpath(".//tei:div", namespaces={"tei": "http://www.tei-c.org/ns/1.0"}):
                    subsection = {"heading": None, "content": ""}
                    sub_head = sub_div.xpath(".//tei:head", namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
                    subsection["heading"] = sub_head[0].text.strip() if sub_head and sub_head[0].text else "Subsection"
                    sub_paragraphs = sub_div.xpath(".//tei:p", namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
                    subsection["content"] = " ".join(p.text.strip() for p in sub_paragraphs if p.text).strip()
                    section["subsections"].append(subsection)
                
                structure["sections"].append(section)

            # Fallback: Use abstract if no sections
            if not structure["sections"]:
                abstract = root.xpath("//tei:abstract", namespaces={"tei": "http://www.tei-c.org/ns/1.0"})
                if abstract and abstract[0].text:
                    structure["sections"].append({
                        "heading": "Abstract",
                        "content": abstract[0].text.strip(),
                        "subsections": []
                    })

            logger.info(f"Parsed structure: title='{structure['title']}', sections={len(structure['sections'])}")
            return structure
        except Exception as e:
            logger.error(f"Error parsing TEI XML: {str(e)}")
            return {"title": "Untitled Document", "sections": []}
def parse_pdf_with_grobid(pdf_path: str) -> Dict[str, Any]:
    cache_dir = os.path.join(os.path.dirname(__file__), "cache")
    os.makedirs(cache_dir, exist_ok=True)
    file_hash = get_file_hash(pdf_path)
    cache_file = os.path.join(cache_dir, f"{file_hash}_grobid.json")

    if os.path.exists(cache_file):
        logger.info(f"Loading cached GROBID results for {pdf_path}")
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

    parser = GrobidParser()
    result = parser.parse_pdf(pdf_path)

    # Fallback to pdfplumber if GROBID fails
    if not result.get("sections") or all(not s["content"] for s in result["sections"]):
        logger.warning("GROBID produced empty structure, falling back to pdfplumber")
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if not text:  # Try OCR if no text
                    try:
                        image = page.to_image()
                        text = pytesseract.image_to_string(image.original)
                    except Exception as e:
                        logger.warning(f"OCR failed for page {i}: {e}")
                        text = ""
                if text.strip():
                    pages.append({"heading": f"Page {i}", "content": text.strip(), "subsections": []})
            result = {"title": os.path.basename(pdf_path), "sections": pages}

    if result and result.get("sections"):
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            logger.info(f"Cached results to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to cache results: {e}")

    return result

# Alternative implementation using the grobid-client-python package
def parse_pdf_with_grobid_client(pdf_path: str) -> Dict[str, Any]:
    """
    Parse PDF using the grobid-client-python package
    Requires: pip install grobid-client-python
    """
    try:
        from grobid_client.grobid_client import GrobidClient

        # Create cache directory if it doesn't exist
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        os.makedirs(cache_dir, exist_ok=True)

        # Generate output path
        output_dir = os.path.join(cache_dir, "grobid_output")
        os.makedirs(output_dir, exist_ok=True)

        # Initialize client
        client = GrobidClient(config_path=None)  # Uses default config

        # Process the PDF
        logger.info(f"Processing PDF with GROBID client: {pdf_path}")

        # Get the directory containing the PDF
        pdf_dir = os.path.dirname(pdf_path)

        # Process the PDF
        client.process(
            "processFulltextDocument",
            pdf_dir,
            output_dir,
            n=1,
            consolidate_header=True,
            tei_coordinates=True,
            force=True,
        )

        # Get the output file path
        pdf_basename = os.path.basename(pdf_path)
        output_file = os.path.join(output_dir, f"{pdf_basename}.tei.xml")

        if os.path.exists(output_file):
            # Parse the TEI XML
            parser = GrobidParser()
            with open(output_file, "r", encoding="utf-8") as f:
                tei_xml = f.read()

            result = parser._parse_tei_xml(tei_xml)
            return result
        else:
            logger.error(f"GROBID client did not generate output file: {output_file}")
            return {"title": "Document", "sections": []}

    except ImportError:
        logger.error(
            "grobid-client-python not installed. Run: pip install grobid-client-python"
        )
        return {"title": "Document", "sections": []}
    except Exception as e:
        logger.error(f"Error using GROBID client: {str(e)}")
        return {"title": "Document", "sections": []}
