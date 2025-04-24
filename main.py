import os
import logging
import argparse
import json
from dotenv import load_dotenv

from huridocs_parser import parse_pdf_with_huridocs
from llm_enricher import LLMEnricher
from mindmap_generator import draw_mindmap

# Configure more detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (if exists)
load_dotenv()


def main(pdf_path, show=True, debug=False):
    """
    Parses a PDF, enriches it with LLM, and generates a mindmap image.

    Args:
        pdf_path (str): Path to the PDF file.
        show (bool): Whether to display the mindmap after generation.
        debug (bool): Whether to enable debug logging.
    """
    if debug:
        # Set logging to DEBUG level if debug flag is enabled
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        logger.info(f"Starting PDF parsing for {pdf_path}...")
        structured_doc = parse_pdf_with_huridocs(pdf_path)

        # Log the structure of the parsed document
        if debug:
            logger.debug(
                f"Parsed document structure: {json.dumps(structured_doc[:5] if isinstance(structured_doc, list) else structured_doc, indent=2)[:500]}..."
            )

        logger.info(
            f"Document parsed successfully. Type: {type(structured_doc).__name__}, Size: {len(structured_doc) if hasattr(structured_doc, '__len__') else 'N/A'}"
        )

        if not structured_doc:
            logger.error(
                f"Failed to parse PDF at {pdf_path}. Please check the file format and structure."
            )
            return

        logger.info("Initializing LLMEnricher...")
        llm_enricher = LLMEnricher(skip_enrichment=args.fast)
        logger.info(f"Using LLM model: {llm_enricher.model}")

        logger.info("Starting document enrichment process...")
        enriched_doc = llm_enricher.enrich_document(structured_doc)

        # Log the enriched document structure
        if debug:
            logger.debug(
                f"Enriched document structure: {json.dumps(enriched_doc, indent=2)[:500]}..."
            )

        if not enriched_doc:
            logger.error("Failed to enrich document.")
            return

        logger.info(
            f"Document enriched successfully. Title: '{enriched_doc.get('title', 'Untitled')}'"
        )
        logger.info(f"Number of sections: {len(enriched_doc.get('sections', []))}")

        structure = {
            "title": enriched_doc.get("title", "Sample Document"),
            "sections": enriched_doc.get("sections", []),
        }

        logger.info("Generating mindmap...")
        output_path = "mindmap.png"
        draw_mindmap(structure, export_path=output_path, show=show)
        logger.info(f"Mindmap generated and saved as {os.path.abspath(output_path)}")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse PDF and generate mindmap")
    parser.add_argument("pdf_path", help="Path to the PDF file to be processed")
    parser.add_argument(
        "--show", action="store_true", help="Show the mindmap after generation"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip content enrichment for faster processing",
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    main(args.pdf_path, show=args.show, debug=args.debug)
