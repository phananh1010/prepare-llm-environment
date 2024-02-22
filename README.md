# Introduction
LLM is huge. It requires a large amount of GPU memory and have long running time if using traditional training methods.
We introduce a guideline to use basic quantization techniques to reduce model memory footprint, improve training time. This document contains step-by-step instruction to fine-tune an LLM that includes necessary technique to accomodate the Llama-8b model on a 24Gb GPU.

# Step 0: install mamba
As mamba is faster than conda, it is strongly recommended to install mamba instead. Use the following code to install and activate mamba. See this [site](https://github.com/conda-forge/miniforge) for more info.
```curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh -u
```
Note: `-u` parameter only used if you have install mamba previously. During installation, specify mamba path to storage partitions, e.g., scratch in `orc.hopper`.
After that, include mamba to PATH environment variable if not done before. 
```
PATH=[install-path]/miniforge3/bin/:$PATH
mamba init
```

# Step 1: create virtual environment with python
```
 mamba create -n env_llm python=3.9
```
Activate the environment then install necessary packages such as pytorch, transformers, etc...
```
mamba install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
python -m pip install accelerate peft bitsandbytes transformers trl
```

# Step 2: set cache directory for huggingface
This is useful if default disk partition could not contain large cached files, and pointing to storage partition is required.
```
export HF_HUB_CACHE=/apps/workspace/data/huggingface-cache
```
or in python:
```
import os
os.environ['HF_HUB_CACHE'] = '/apps/workspace/data/huggingface-cache'
```
# Step 3: refer to the `fine-tuning.py`
This code has been sucessfully run in a GPU with 24G of Memory. The whole training only requires 13Gb.
