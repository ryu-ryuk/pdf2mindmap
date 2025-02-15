"""
    Extracts text from PDF files using pdfplumber and preseves document structure
"""


import pdfplumber


def extract_text(pdf_path):
    text_content=""


    try:
        with pdfplumber.open(pdf_path) ad pdf:
            for page in pdf.pages:
    
                page_text = page.extract_text()

                # In case of fail, handling~
                if page_text:
                    text_content += page_text + "\n"

                else:
                    print(f"Warning: No text found on page {page.page_number}")
    except Exception as e:

        print(f"Error extracting text from {pdf.path}: {e}")

    return text_content

