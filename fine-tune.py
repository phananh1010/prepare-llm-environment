# NOTE: this code is referred from `https://github.com/huggingface/peft/blob/main/examples/fp4_finetuning/finetune_fp4_opt_bnb_peft.py`


import os

import torch
import torch.nn as nn
import transformers
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from peft import LoraConfig, get_peft_model

base_model = "NousResearch/Llama-2-7b-chat-hf"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# -*- coding: utf-8 -*-

free_in_GB = int(torch.cuda.mem_get_info()[0] / 1024**3)
max_memory = f"{free_in_GB-2}GB"

n_gpus = torch.cuda.device_count()
max_memory = {i: max_memory for i in range(n_gpus)}

model = AutoModelForCausalLM.from_pretrained(
    base_model,
    max_memory=max_memory,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    ),
    torch_dtype=torch.float16,
)

tokenizer = AutoTokenizer.from_pretrained(base_model)

print(model)

for param in model.parameters():
    param.requires_grad = False  # freeze the model - train adapters later
    if param.ndim == 1:
        # cast the small parameters (e.g. layernorm) to fp32 for stability
        param.data = param.data.to(torch.float32)

class CastOutputToFloat(nn.Sequential):
    def forward(self, x):
        return super().forward(x).to(torch.float32)


model.lm_head = CastOutputToFloat(model.lm_head)

def print_trainable_parameters(model):
    """
    Prints the number of trainable parameters in the model.
    """
    trainable_params = 0
    all_param = 0
    for _, param in model.named_parameters():
        all_param += param.numel()
        if param.requires_grad:
            trainable_params += param.numel()
    print(
        f"trainable params: {trainable_params} || all params: {all_param} || trainable%: {100 * trainable_params / all_param}"
    )


config = LoraConfig(
    r=64,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "out_proj", "fc1", "fc2"],
    lora_dropout=0.01,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, config)
print_trainable_parameters(model)

# Verifying the datatypes.
dtypes = {}
for _, p in model.named_parameters():
    dtype = p.dtype
    if dtype not in dtypes:
        dtypes[dtype] = 0
    dtypes[dtype] += p.numel()
total = 0
for k, v in dtypes.items():
    total += v
for k, v in dtypes.items():
    print(k, v, v / total)

"""### Training"""

data = load_dataset("Abirate/english_quotes")
data = data.map(lambda samples: tokenizer(samples["quote"]), batched=True)

# Compare before and after training for the same prompt. The goal is to make the model to output slightly similar to Enstein
print ('#########BEFORE TRAINING############')
batch = tokenizer("Two things are infinite: ", return_tensors="pt")

model.config.use_cache = False  # silence the warnings. Please re-enable for inference!
model.eval()
with torch.cuda.amp.autocast():
    output_tokens = model.generate(**batch, max_new_tokens=50)

print("\n\n", tokenizer.decode(output_tokens[0], skip_special_tokens=True))

print ('############BEGIN TRAINING############')
trainer = transformers.Trainer(
    model=model,
    train_dataset=data["train"],
    args=transformers.TrainingArguments(
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        warmup_steps=10,
        max_steps=20,
        learning_rate=3e-4,
        fp16=True,
        logging_steps=1,
        output_dir="outputs",
    ),
    data_collator=transformers.DataCollatorForLanguageModeling(tokenizer, mlm=False),
)
model.config.use_cache = False  # silence the warnings. Please re-enable for inference!
trainer.train()

print ('#############AFTER TRAINING##############')
batch = tokenizer("Two things are infinite: ", return_tensors="pt")

model.config.use_cache = False  # silence the warnings. Please re-enable for inference!
model.eval()
with torch.cuda.amp.autocast():
    output_tokens = model.generate(**batch, max_new_tokens=50)

print("\n\n", tokenizer.decode(output_tokens[0], skip_special_tokens=True))
