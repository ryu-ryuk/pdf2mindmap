"""
Flask web interface for uploading PDF files and displaying the generated mind map.
"""

from flask import Flask, request, render_template, redirect, url_for, flash
import os

from nlp_processing.semantic_analysis import extract_summary

# Set up the Hugging Face model for summarization
# Import functions from our modules
from pdf2mindmap.pdf_processing.extract_text import extract_text
from pdf2mindmap.nlp_processing.semantic_analysis import extract_keywords
from pdf2mindmap.mindmap_generation.create_mindmap import create_mindmap

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session management

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("No file part")
            return redirect(request.url)
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)
        # Save the file
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)
        
        # After extracting the basic text
        text = extract_text(file_path)
        # If a user has provided additional keywords, process with Hugging Face summarization
        user_keywords = request.form.get("keywords", "").strip()
        if user_keywords:
            advanced_summary = extract_summary(text)
            # You can then combine the summary with the original text or extract further keywords
            text += "\n" + advanced_summary

        # Continue with extracting keywords using spaCy or your existing method
        keywords = extract_keywords(text)
        create_mindmap(keywords)

        # You can then redirect or show a success page.
        flash("Mind map generated successfully!")
        return redirect(url_for("upload_file"))
    return render_template("upload.html")

if __name__ == "__main__":
    app.run(debug=True)
