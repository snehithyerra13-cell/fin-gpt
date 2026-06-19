import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
from torch.optim import AdamW
from datasets import load_dataset, Dataset
from sklearn.metrics import classification_report
from sklearn.utils.class_weight import compute_class_weight
from sklearn.model_selection import train_test_split
import numpy as np
from tqdm import tqdm
import os
import PyPDF2

# Check GPU
print("CUDA available:", torch.cuda.is_available())
print("Device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")

# 1. Load Dataset
try:
    dataset = load_dataset("nickmuchi/financial-classification", trust_remote_code=True)
except Exception as e:
    print(f"Error loading dataset: {e}")
    exit(1)

# 2. Mock Document Type Labels with 9 Categories
def assign_document_type(text):
    if not isinstance(text, str):
        print(f"Warning: Non-string text found: {text}")
        return "financial_news_article"
    text = text.lower()
    if "balance sheet" in text or "assets" in text or "liabilities" in text:
        return "balance_sheet"
    elif "income" in text or "revenue" in text or "profit" in text:
        return "income_statement"
    elif "cash flow" in text or "cashflow" in text:
        return "cash_flow_statement"
    elif "10-k" in text or "annual report" in text:
        return "10k_filing"
    elif "agreement" in text or "contract" in text or "loan agreement" in text:
        return "contract_agreement"
    elif "audit" in text or "auditor" in text:
        return "audit_report"
    elif "prospectus" in text or "offering" in text:
        return "prospectus"
    elif "invoice" in text or "billing" in text:
        return "invoice"
    else:
        return "financial_news_article"

# Add mock labels to the dataset with debugging
def apply_document_type(example):
    doc_type = assign_document_type(example["text"])
    if not isinstance(doc_type, str):
        print(f"Warning: Non-string document_type returned for text: {example['text'][:50]}... -> {doc_type}")
        doc_type = "financial_news_article"
    return {"document_type": doc_type}

# Apply mapping and clean dataset
dataset = dataset.map(apply_document_type)
dataset = dataset["train"].filter(lambda x: isinstance(x["text"], str))

# 3. Label Mapping
label_list = [
    "balance_sheet",
    "income_statement",
    "cash_flow_statement",
    "10k_filing",
    "financial_news_article",
    "contract_agreement",
    "audit_report",
    "prospectus",
    "invoice"
]
label_map = {label: idx for idx, label in enumerate(label_list)}
num_labels = len(label_list)
print("Number of labels:", num_labels)
print("Label list:", label_list)

# Debug document_type values
print("Checking document_type values...")
invalid_count = 0
for i, item in enumerate(dataset):
    if not isinstance(item["document_type"], str):
        print(f"Invalid document_type at index {i}: text={item['text'][:50]}..., document_type={item['document_type']}")
        invalid_count += 1
if invalid_count == 0:
    print("All document_type values are strings.")
else:
    print(f"Found {invalid_count} invalid document_type values.")

# Check unique labels
unique_labels = sorted(set(item["document_type"] for item in dataset))
print("Unique labels in dataset:", unique_labels)
if len(unique_labels) < num_labels:
    print(f"WARNING: Only {len(unique_labels)} unique labels found, but {num_labels} expected. Missing labels may reduce performance.")

# Print label distribution
label_counts = {label: sum(1 for x in dataset if x["document_type"] == label) for label in label_list}
print("Label distribution:", label_counts)

# Split dataset with stratification
texts = [item["text"] for item in dataset]
labels = []
for item in dataset:
    doc_type = item["document_type"]
    if not isinstance(doc_type, str):
        print(f"Warning: Non-string document_type in dataset: text={item['text'][:50]}..., document_type={doc_type}")
        doc_type = "financial_news_article"
    labels.append(label_map[doc_type])
try:
    train_indices, test_indices = train_test_split(
        range(len(dataset)),
        test_size=0.2,
        random_state=42,
        stratify=labels
    )
except ValueError as e:
    print(f"Stratification error: {e}")
    print("Falling back to non-stratified split.")
    train_indices, test_indices = train_test_split(
        range(len(dataset)),
        test_size=0.2,
        random_state=42
    )
print(f"Train indices count: {len(train_indices)}, Test indices count: {len(test_indices)}")
train_dataset = dataset.select(train_indices)
test_dataset = dataset.select(test_indices)
dataset = {"train": train_dataset, "test": test_dataset}

# Debug train and test dataset
print("Train dataset label distribution:", {label: sum(1 for x in dataset["train"] if x["document_type"] == label) for label in label_list})
print("Test dataset label distribution:", {label: sum(1 for x in dataset["test"] if x["document_type"] == label) for label in label_list})

# 4. Tokenization and Dataset Wrapping
model_name = "ProsusAI/finbert"
tokenizer = AutoTokenizer.from_pretrained(model_name)

class FinancialClassificationDataset(Dataset):
    def init(self, data, tokenizer, max_len=128):
        self._data = data
        self.tokenizer = tokenizer
        self.max_len = max_len

    def len(self):
        return len(self._data)

    def getitem(self, idx):
        text = self._data[idx]["text"] or ""
        doc_type = self._data[idx]["document_type"]
        if not isinstance(doc_type, str):
            print(f"Warning: Non-string document_type at index {idx}: text={text[:50]}..., document_type={doc_type}")
            doc_type = "financial_news_article"
        try:
            label = label_map[doc_type]
        except KeyError:
            print(f"KeyError: Invalid document_type '{doc_type}' at index {idx}: text={text[:50]}...")
            label = label_map["financial_news_article"]
        encoding = self.tokenizer(
            text,
            padding="max_length",
            truncation=True,
            max_length=self.max_len,
            return_tensors="pt",
        )
        item = {key: val.squeeze(0) for key, val in encoding.items()}
        item["labels"] = torch.tensor(label)
        return item

    def getitems(self, indices):
        return [self.getitem(idx) for idx in indices]

train_dataset = FinancialClassificationDataset(dataset["train"], tokenizer)
val_dataset = FinancialClassificationDataset(dataset["test"], tokenizer)

train_loader = DataLoader(train_dataset, batch_size=8, shuffle=True, num_workers=0)
val_loader = DataLoader(val_dataset, batch_size=8, num_workers=0)

# 5. Compute Class Weights
labels = []
for item in dataset["train"]:
    doc_type = item["document_type"]
    if not isinstance(doc_type, str):
        print(f"Warning: Non-string document_type in train dataset: text={item['text'][:50]}..., document_type={doc_type}")
        doc_type = "financial_news_article"
    labels.append(label_map[doc_type])
unique_label_indices = np.unique(labels)
if len(unique_label_indices) < num_labels:
    print(f"WARNING: Only {len(unique_label_indices)} unique label indices found in training data.")

# Compute weights for observed labels
class_weights = compute_class_weight("balanced", classes=unique_label_indices, y=labels)

# Ensure weights for all 9 labels
full_class_weights = np.ones(num_labels)  # Default weight = 1.0 for missing labels
for idx, weight in enumerate(class_weights):
    full_class_weights[unique_label_indices[idx]] = weight
class_weights = torch.tensor(full_class_weights, dtype=torch.float)
print("Class weights shape:", class_weights.shape)

# 6. Model and Optimizer
model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=num_labels,
    ignore_mismatched_sizes=True
)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
class_weights = class_weights.to(device)
optimizer = AdamW(model.parameters(), lr=2e-5)
total_steps = len(train_loader) * 3  # 3 epochs
scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=0, num_training_steps=total_steps)

# 7. Training Loop with Early Stopping
epochs = 3
best_val_loss = float("inf")
patience = 1
save_path = "models/classification_finbert_financial_docs"

for epoch in range(epochs):
    model.train()
    loop = tqdm(train_loader, desc=f"Epoch {epoch + 1}")
    for batch in loop:
        batch = {k: v.to(device) for k, v in batch.items()}
        outputs = model(**batch)
        loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)
        loss = loss_fn(outputs.logits, batch["labels"])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        scheduler.step()
        loop.set_postfix(loss=loss.item())

    # Validation
    model.eval()
    val_loss = 0
    with torch.no_grad():
        for batch in val_loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            outputs = model(**batch)
            val_loss += loss_fn(outputs.logits, batch["labels"]).item()
    val_loss /= len(val_loader)
    print(f"Epoch {epoch + 1}, Validation Loss: {val_loss}")

    if val_loss < best_val_loss:
        best_val_loss = val_loss
        epochs_no_improve = 0
        os.makedirs(save_path, exist_ok=True)
        model.save_pretrained(save_path)
        tokenizer.save_pretrained(save_path)
    else:
        epochs_no_improve += 1
        if epochs_no_improve >= patience:
            print("Early stopping triggered")
            break

# 8. Evaluation
model.eval()
all_preds = []
all_labels = []

with torch.no_grad():
    for batch in val_loader:
        batch = {k: v.to(device) for k, v in batch.items()}
        outputs = model(**batch)
        preds = torch.argmax(outputs.logits, dim=1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(batch["labels"].cpu().numpy())

# Get unique labels in validation set
unique_val_labels = sorted(set(all_labels))
valid_target_names = [label_list[i] for i in unique_val_labels]

print("\nClassification Report:")
#print(classification_report(all_labels, all_preds, target_names=valid_target_names))

print(f"\n✅ Model and tokenizer saved to: {save_path}")

# 9. Function to Classify New Documents
def classify_document(text, model, tokenizer, device, max_len=128):
    model.eval()
    encoding = tokenizer(
        text,
        padding="max_length",
        truncation=True,
        max_length=max_len,
        return_tensors="pt",
    )
    encoding = {k: v.to(device) for k, v in encoding.items()}
    with torch.no_grad():
        outputs = model(**encoding)
        probs = torch.softmax(outputs.logits, dim=1)
        pred = torch.argmax(probs, dim=1).item()
    return label_list[pred], probs.cpu().numpy()

# 10. Function for Long Documents (Chunking)
def chunk_text(text, tokenizer, max_len=128, overlap=50):
    tokens = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    for i in range(0, len(tokens), max_len - overlap):
        chunk = tokens[i:i + max_len]
        chunks.append(tokenizer.decode(chunk))
    return chunks

def classify_long_document(text, model, tokenizer, device, max_len=128):
    chunks = chunk_text(text, tokenizer, max_len)
    probs = []
    model.eval()
    for chunk in chunks:
        encoding = tokenizer(chunk, padding="max_length", truncation=True, max_length=max_len, return_tensors="pt")
        encoding = {k: v.to(device) for k, v in encoding.items()}
        with torch.no_grad():
            outputs = model(**encoding)
            probs.append(torch.softmax(outputs.logits, dim=1).cpu().numpy())
    avg_probs = np.mean(probs, axis=0)
    pred = np.argmax(avg_probs)
    return label_list[pred], avg_probs

# 11. Function to Extract Text from PDF
def extract_pdf_text(pdf_path):
    try:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file '{pdf_path}' not found")
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    print(f"Warning: No text extracted from page {page_num}")
                text += page_text + "\n"
            if not text.strip():
                raise ValueError("No text extracted from PDF")
            return text.strip()
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        return None
    except Exception as e:
        print(f"Error reading PDF: {str(e)}")
        return None

# Example usage with PDF
pdf_path = r"C:\Users\surya\OneDrive\Desktop\test pdf summary.pdf"  # Replace with your PDF file path
pdf_text = extract_pdf_text(pdf_path)
if pdf_text:
    label = classify_long_document(pdf_text, model, tokenizer, device)
    print(f"Predicted document type: {label}")
    # print(f"Probabilities: {probs}")  # ← This line is now commented out
else:
    print("Failed to extract text from PDF.")