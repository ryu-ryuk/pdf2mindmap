import spacy
from transformers import pipeline


def extract_keywords(text):
    
    try:
        # Load a small English model for now
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        
        # Extract the keywords (noun phrases) which often represent key concepts
        
        keywords = [chunk.text.strip() for chunk in doc.noun_chunks] 
        
        return list(set(keywords)) # removing duplicates
    
    except Exception as e:
        print(f"Error during NLP processing: {e}")
        return []
    
    

def extract_summary(text, max_length=130, min_length=30):
    """
    Uses Hugging Face's summarization pipeline to create a summary of the PDF text.
    """
    try:
        summarizer = pipeline("summarization")
        summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print(f"Error in advanced summarization: {e}")
        return ""
