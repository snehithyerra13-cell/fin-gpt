# general_finance_chatbot.py

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Load WiroAI Finance model
print("🔄 Loading model...")
model_name = "WiroAI/WiroAI-Finance-Qwen-1.5B"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
print("✅ Model loaded.")

def ask_model(question):
    prompt = (
        "You are a financial expert. "
        "Answer the question clearly in one short sentence. Do not provide options. "
        f"Question: {question}\nAnswer:"
    )
    inputs = tokenizer(prompt, return_tensors="pt")
    output = model.generate(
        inputs.input_ids,
        max_new_tokens=100,
        do_sample=False,
        temperature=0.7,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.eos_token_id
    )
    result = tokenizer.decode(output[0], skip_special_tokens=True)
    return result.replace(prompt, "").strip()

# CLI loop
print("\n💬 General Finance Q&A Chatbot\nType 'exit' to quit.")
while True:
    question = input("\n💼 Ask a finance question: ").strip()
    if question.lower() == "exit":
        print("👋 Exiting.")
        break
    answer = ask_model(question)
    print(f"📘 Answer: {answer}")