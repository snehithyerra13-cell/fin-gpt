---
license: apache-2.0
library_name: transformers
pipeline_tag: text-generation
datasets:
- Josephgflowers/Finance-Instruct-500k
base_model:
- deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
- Qwen/Qwen2.5-Math-1.5B
---


# WiroAI-Finance-Qwen-1.5B
<!-- markdownlint-disable first-line-h1 -->
<!-- markdownlint-disable html -->
<!-- markdownlint-disable no-duplicate-header -->

<div align="center">
  <img src="https://huggingface.co/WiroAI/wiroai-turkish-llm-9b/resolve/main/wiro_logo.png" width="15%" alt="Wiro AI" />
</div>
<hr>
<div align="center" style="line-height: 1;">
  <a href="https://www.wiro.ai/" target="_blank" style="margin: 2px;">
    <img alt="Homepage" src="https://huggingface.co/WiroAI/wiroai-turkish-llm-9b/resolve/main/homepage.svg" style="display: inline-block; vertical-align: middle;"/>
  </a>
  <a href="https://wiro.ai/tools?search=&categories=chat&tags=&page=0" target="_blank" style="margin: 2px;">
    <img alt="Chat" src="https://huggingface.co/WiroAI/wiroai-turkish-llm-9b/resolve/main/chat.svg" style="display: inline-block; vertical-align: middle;"/>
  </a>
  <a href="https://huggingface.co/WiroAI" target="_blank" style="margin: 2px;">
    <img alt="Hugging Face" src="https://huggingface.co/WiroAI/wiroai-turkish-llm-9b/resolve/main/huggingface.svg" style="display: inline-block; vertical-align: middle;"/>
  </a>
</div>
<div align="center" style="line-height: 1;">
  <a href="https://instagram.com/wiroai" target="_blank" style="margin: 2px;">
    <img alt="Instagram Follow" src="https://img.shields.io/badge/Instagram-wiroai-555555?logo=instagram&logoColor=white&labelColor=E4405F" style="display: inline-block; vertical-align: middle;"/>
  </a>
    <a href="https://x.com/wiroai" target="_blank" style="margin: 2px;">
    <img alt="X Follow" src="https://img.shields.io/badge/X-wiroai-555555?logo=x&logoColor=white&labelColor=000000" style="display: inline-block; vertical-align: middle;"/>
  </a>
</div>
<div align="center" style="line-height: 1;">
  <a href="https://wiro.ai/agreement/terms-of-service" style="margin: 2px;">
    <img alt="License" src="https://img.shields.io/badge/License-apache 2.0-f5de53?&color=f5de53" style="display: inline-block; vertical-align: middle;"/>
  </a>
</div>


# 🚀 Meet with WiroAI/WiroAI-Finance-Qwen-1.5B! A robust language model with more finance knowledge support! 🚀

## 🌟 Key Features

- Fine-tuned with 500,000+ high-quality finance instructions. ([Josephgflowers/Finance-Instruct-500k](https://huggingface.co/datasets/Josephgflowers/Finance-Instruct-500k))
- LoRA method was used for fine-tuning without quantization.
- Adapted to finance expertise.
- Built on Qwen's architecture

📝 Model Details
The model is the finance data fine-tuned version of Qwen model family. This model has been trained using Supervised Fine-Tuning (SFT) on carefully curated high-quality finance instructions. Please note that training data includes English and Chinese instructions, and this model rarely mix the two languages.

## Usage

### Transformers Pipeline

```python
import transformers
import torch


model_id = "WiroAI/WiroAI-Finance-Qwen-1.5B"

pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)

pipeline.model.eval()

messages = [
    {"role": "system", "content": "You are a finance chatbot developed by Wiro AI"},
    {"role": "user", "content": "How can central banks balance the trade-off between controlling inflation and maintaining economic growth, especially in an environment of high public debt and geopolitical uncertainty?"
  },
]

terminators = [
    pipeline.tokenizer.eos_token_id,
    pipeline.tokenizer.convert_tokens_to_ids("<｜end▁of▁sentence｜>")
]

outputs = pipeline(
    messages,
    max_new_tokens=512,
    eos_token_id=terminators,
    do_sample=True,
    temperature=0.9,
)

print(outputs[0]["generated_text"][-1]['content'])
```

```markdown
Central banks aim to strike a balance between controlling inflation and maintaining economic growth amidst high public debt and geopolitical uncertainties. They employ various policy tools and measures to achieve this objective.

First, central banks employ monetary policy to influence aggregate demand and price levels. The primary policy tools include:
1. Interest rates: Central banks adjust interest rates to manage the cost of borrowing and reduce inflation. Lower interest rates stimulate demand, while higher rates can curtail economic activity.
2. Open market operations: Central banks buy or sell government securities to influence the money supply and drive economic growth.
3. Government spending and taxation: Central banks influence fiscal policy to adjust government spending and taxation, which directly impacts economic activity and inflation.

Second, central banks utilize financial tools to stabilize the financial system and mitigate risks associated with high public debt and geopolitical uncertainties. Key measures include:
1. Capital controls: Central banks set limits on the amount of capital available to financial institutions, which helps manage risk and prevent market bubbles.
2. Financial regulations: Central banks introduce regulations to prevent excessive credit, debt, and fraud, which can contribute to inflation and systemic financial instability.
3. Financial reform: Central banks work towards improving the regulatory framework and infrastructure to enhance financial stability and support economic growth.

Furthermore, central banks consider the impact of geopolitical uncertainties on their operations. They implement measures to strengthen international relations, promote dialogue, and facilitate cooperation among countries to address global challenges collectively.

In conclusion, central banks balance the trade-off between controlling inflation and maintaining economic growth by employing a combination of monetary and financial policies, capital controls, regulatory reforms, and international cooperation. These measures help them navigate the complexities of high public debt, political instability, and economic uncertainty while pursuing their core objectives of economic stability and growth.
```

## 🤝 License and Usage
This model is provided under apache 2.0 license. Please review the license terms before use.

## 📫 Contact and Support
For questions, suggestions, and feedback, please open an issue on HuggingFace or contact us directly from our website.

## Citation

```none
@article{WiroAI,
  title={WiroAI/WiroAI-Finance-Qwen-1.5B},
  author={Abdullah Bezir, Furkan Burhan Türkay, Cengiz Asmazoğlu},
  year={2025},
  url={https://huggingface.co/WiroAI/WiroAI-Finance-Qwen-1.5B}
}
```