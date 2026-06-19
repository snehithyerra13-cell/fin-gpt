import torch
import gc
from transformers import BartTokenizer, BartForConditionalGeneration, Trainer, TrainingArguments, GenerationConfig
from datasets import load_dataset
import re
import PyPDF2
import os

# Step 1: Load the smaller pre-trained DistilBART model and tokenizer
print("Step 1: Loading model and tokenizer...")
model_name = "sshleifer/distilbart-cnn-6-6"
tokenizer = BartTokenizer.from_pretrained(model_name)
model = BartForConditionalGeneration.from_pretrained(model_name)

# Fix Transformers warning and ensure decoder_start_token_id
model.generation_config = GenerationConfig(
    max_length=142,
    min_length=56,
    early_stopping=True,
    num_beams=4,
    length_penalty=2.0,
    no_repeat_ngram_size=3,
    forced_bos_token_id=0,
    decoder_start_token_id=2  # Set for DistilBART
)

# Step 2: Load the BillSum dataset (California subset)
print("Step 2: Loading dataset...")
dataset = load_dataset("billsum", split="ca_test")

# Split the dataset into train and test manually
train_size = int(0.9 * len(dataset))
train_subset = dataset.select(range(train_size))
test_subset = dataset.select(range(train_size, len(dataset)))

# Step 3: Preprocess the dataset
print("Step 3: Preprocessing dataset...")
def preprocess_function(examples):
    inputs = examples["text"]
    targets = examples["summary"]
    model_inputs = tokenizer(inputs, max_length=512, truncation=True, padding="max_length")
    labels = tokenizer(targets, max_length=128, truncation=True, padding="max_length")
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

train_dataset = train_subset.map(preprocess_function, batched=True)
test_dataset = test_subset.map(preprocess_function, batched=True)

# Step 4: Define training arguments with a fixed learning rate
print("Step 4: Defining training arguments...")
training_args = TrainingArguments(
    output_dir="./distilbart_finetuned_billsum_fixed_lr",
    num_train_epochs=1,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    learning_rate=3e-5,
    lr_scheduler_type="constant",
    warmup_steps=0,
    weight_decay=0.01,
    logging_dir="./logs",
    logging_steps=10,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
)

# Step 5: Initialize Trainer
print("Step 5: Initializing Trainer...")
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    processing_class=tokenizer,
)

# Step 6: Fine-tune the model
print("Step 6: Training model...")
trainer.train()

# Step 7: Save the fine-tuned model
print("Step 7: Saving model and tokenizer...")
model.save_pretrained("./distilbart_finetuned_billsum_fixed_lr_model")
model.generation_config.save_pretrained("./distilbart_finetuned_billsum_fixed_lr_model")
tokenizer.save_pretrained("./distilbart_finetuned_billsum_fixed_lr_model")
# Clear memory
trainer = None
train_dataset = None
test_dataset = None
gc.collect()
torch.cuda.empty_cache()  # If using GPU
# Use in-memory model instead of reloading to avoid paging file issue
model.generation_config.decoder_start_token_id = 2

# Step 8: Define a function to summarize the financial document
def summarize_document(text):
    print("Step 8: Summarizing document...")
    device = next(model.parameters()).device
    inputs = tokenizer(text[:10000], return_tensors="pt", max_length=512, truncation=True)  # Limit input
    inputs = {k: v.to(device) for k, v in inputs.items()}
    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=150,
        min_length=50,
        length_penalty=1.0,
        num_beams=6,
        early_stopping=True,
        no_repeat_ngram_size=3,
        decoder_start_token_id=2  # Explicitly set for DistilBART
    )
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    summary = summary.replace("Existing law provides for the licensure and regulation of", "")
    summary = summary.replace("This bill would include a new AI-driven", "")
    return summary.strip()

# Step 9: Define a function to mask sensitive financial information
def mask_financial_info(text):
    print("Step 9: Masking sensitive information...")
    text = re.sub(r'\$\d{1,3}(,\d{3})*(\.\d+)?\s?(million|billion|M|B|\d+)', '[REDACTED]', text, flags=re.IGNORECASE)
    text = re.sub(r'[€£¥]\d+(\.\d+)?\s?(million|billion|M|B|\d+)', '[REDACTED]', text, flags=re.IGNORECASE)
    text = re.sub(r'\d+(\.\d+)?\%', '[REDACTED]', text)
    text = re.sub(r'\b(?!19\d{2}|20\d{2})\d+(\.\d+)?\b(?!\s*(million|billion|M|B|%))', '[REDACTED]', text)
    return text

# Step 10: Read the input PDF file and clean text
def clean_text(text):
    return ''.join(c for c in text if ord(c) < 128)  # Remove non-ASCII characters

print("Step 10: Reading input PDF...")
input_pdf_path = r"C:\Users\surya\OneDrive\Desktop\test.pdf"
try:
    if not os.path.exists(input_pdf_path):
        raise FileNotFoundError(f"Input PDF file '{input_pdf_path}' not found")
    with open(input_pdf_path, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        financial_doc = ""
        for page_num, page in enumerate(pdf_reader.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                print(f"Warning: No text extracted from page {page_num}")
            financial_doc += text + "\n"
        financial_doc = clean_text(financial_doc)  # Clean text
        if not financial_doc.strip():
            raise ValueError("No text extracted from PDF")
    print("Extracted text length:", len(financial_doc))
except FileNotFoundError as e:
    print(f"Error: {str(e)}")
    exit(1)
except Exception as e:
    print(f"Error reading PDF: {str(e)}")
    exit(1)

# Step 11: Summarize the document
try:
    summary = summarize_document(financial_doc)
except Exception as e:
    print(f"Error summarizing document: {str(e)}")
    exit(1)

# Step 12: Mask sensitive information
try:
    masked_summary = mask_financial_info(summary)
    print("Masked summary:", masked_summary)
except Exception as e:
    print(f"Error masking summary: {str(e)}")
    exit(1)

# Step 13: Generate text report
def generate_text_report(masked_summary, output_path="output_summary.txt"):
    print("Step 13: Generating text report...")
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write("Masked Financial Document Summary\n")
            file.write("June 16, 2025\n")
            file.write("\n" + "="*50 + "\n")
            file.write(masked_summary + "\n")
        
        print(f"Text report generated successfully: {output_path}")
        print("Text file exists:", os.path.exists(output_path))
    except Exception as e:
        print(f"Error generating text report: {str(e)}")
        raise
