import os
import fitz  # PyMuPDF
import torch
from transformers import AutoTokenizer, AutoModelForQuestionAnswering

# Load the Roberta QA model (finance-focused)
print("🔄 Loading model...")
model_name = "deepset/roberta-base-squad2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForQuestionAnswering.from_pretrained(model_name)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
print("✅ Model loaded.")

# Extract text from up to 2 pages of the PDF
def extract_pdf_text(path, max_pages=2):
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    doc = fitz.open(path)
    text = ""
    for i in range(min(len(doc), max_pages)):
        text += doc[i].get_text()
    return text.strip()

# Perform extractive QA using Roberta model
def ask_model_from_pdf(pdf_text, question):
    inputs = tokenizer(question, pdf_text, return_tensors="pt", truncation=True, max_length=512).to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)

    start_scores = outputs.start_logits
    end_scores = outputs.end_logits

    start_idx = torch.argmax(start_scores)
    end_idx = torch.argmax(end_scores) + 1

    if start_idx >= end_idx:
        return "⚠ Sorry, I couldn't find a clear answer in the PDF."

    answer_tokens = inputs["input_ids"][0][start_idx:end_idx]
    answer = tokenizer.decode(answer_tokens, skip_special_tokens=True)
    return answer.strip()

# CLI loop
def main():
    print("\n📄 PDF-Based Finance Q&A\nType 'exit' to quit.")
    pdf_path = input("\nEnter full path of PDF file: ").strip().strip('"').strip("'")
    
    if not os.path.exists(pdf_path):
        print("❌ PDF file not found. Exiting.")
        return

    try:
        pdf_text = extract_pdf_text(pdf_path)
        if not pdf_text:
            print("⚠ PDF is empty or unreadable.")
            return
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return

    while True:
        question = input("\n💬 Ask a question from the PDF (or type 'exit'): ").strip()
        if question.lower() == "exit":
            print("👋 Exiting.")
            break
        answer = ask_model_from_pdf(pdf_text, question)
        print(f"📘 Answer: {answer}")

if _name_ == "_main_":
    main()