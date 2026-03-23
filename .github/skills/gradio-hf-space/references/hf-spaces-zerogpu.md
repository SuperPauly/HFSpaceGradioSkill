# HuggingFace Spaces — Zero GPU, Multi-Model Loading, and Limits

## Table of Contents

1. [Zero GPU overview](#1-zero-gpu-overview)
2. [The `@spaces.GPU` decorator in depth](#2-the-spacesGPU-decorator-in-depth)
3. [HuggingFace Spaces hard limits](#3-huggingface-spaces-hard-limits)
4. [Multi-model loading strategies](#4-multi-model-loading-strategies)
5. [Memory optimisation techniques](#5-memory-optimisation-techniques)
6. [UI patterns that feel fast despite GPU cold-starts](#6-ui-patterns-that-feel-fast-despite-gpu-cold-starts)
7. [Persistent storage and caching](#7-persistent-storage-and-caching)
8. [Debugging and profiling on Spaces](#8-debugging-and-profiling-on-spaces)

---

## 1. Zero GPU overview

**HuggingFace Spaces Zero GPU** (a.k.a. "ZeroGPU") lets you publish GPU-powered demos
without a dedicated GPU instance. The runtime:

- Maintains a pool of NVIDIA A100 (80 GB) GPUs shared across users.
- Allocates one to your Space for the duration of a single `@spaces.GPU`-decorated
  function call, then reclaims it.
- Charges no per-minute fee — you pay only in community usage quota.

This means the GPU is **not always attached** to your process. Any code that runs outside
a `@spaces.GPU` function sees `torch.cuda.is_available() == False`.

### When to use Zero GPU

- Demos, prototypes, and apps with infrequent or bursty GPU demand.
- Research previews where guaranteed latency is not critical.
- Applications that can queue users (Gradio's `demo.queue()`) gracefully.

### When NOT to use Zero GPU

- Real-time streaming at < 200 ms latency (cold-start allocation takes 1–5 s).
- High-throughput production services (use a dedicated GPU Space or Inference Endpoints).
- Applications that need the GPU between requests (e.g., maintaining a KV-cache).

---

## 2. The `@spaces.GPU` decorator in depth

### Installation

```bash
pip install spaces
```

The `spaces` package is pre-installed in all HuggingFace Spaces Docker images.

### Basic usage

```python
import spaces
import torch

@spaces.GPU
def classify(image):
    # GPU is guaranteed available inside here
    model = load_model()
    return model(image)
```

### `duration` parameter

```python
@spaces.GPU(duration=120)   # request up to 120 s of GPU time
def generate_long_video(prompt):
    ...
```

- Default: **60 seconds**.
- Maximum: **180 seconds** (hard cap imposed by ZeroGPU runtime).
- Set `duration` as tight as you can — users queue for the GPU, so long durations reduce
  throughput for everyone.
- If your function finishes early, the GPU is released immediately regardless of
  `duration`.

### What happens on timeout

If your function exceeds `duration` seconds, the ZeroGPU runtime raises
`spaces.ZeroGPUError`. Wrap GPU calls defensively:

```python
@spaces.GPU(duration=90)
def safe_generate(prompt):
    try:
        return model(prompt).images[0]
    except Exception as e:
        return gr.Warning(f"Generation failed: {e}")
```

### Nesting and composition

Do **not** call one `@spaces.GPU` function from inside another. The inner decorator will
try to re-acquire the GPU and raise a `ZeroGPUError`. Instead, extract shared logic into
a plain helper function and call it from the decorated function.

```python
# ✅ Correct
def _run_model(prompt):   # plain function, no decorator
    return model(prompt)

@spaces.GPU
def generate(prompt):
    return _run_model(prompt)

# ❌ Wrong — will raise ZeroGPUError
@spaces.GPU
def inner(prompt):
    ...

@spaces.GPU
def outer(prompt):
    return inner(prompt)   # double-acquisition!
```

### Model placement strategy

```python
# Load to CPU at import time (fast startup, no GPU needed yet)
model = MyModel.from_pretrained("org/model", torch_dtype=torch.float16)
# model is on CPU here

@spaces.GPU
def infer(prompt):
    model.to("cuda")      # move to GPU for this call
    result = model(prompt)
    model.to("cpu")       # move back so GPU can be reclaimed cleanly
    torch.cuda.empty_cache()
    return result
```

Moving back to CPU inside the decorated function is optional but recommended for large
models — it ensures the GPU is free for other users immediately after your function
returns.

---

## 3. HuggingFace Spaces hard limits

### Resource limits (2025 figures — check the HF docs for updates)

| Resource | Free / Community tier | Pro / Org tier |
|---|---|---|
| CPU RAM | 16 GB | 32 GB (varies by hardware) |
| GPU | Shared (Zero GPU) | Dedicated A10G/A100 available |
| GPU RAM | ~40–80 GB per call (A100) | Depends on selected hardware |
| Disk (ephemeral) | 50 GB | 50 GB |
| Disk (persistent) | Not included | `/data` volume (paid add-on) |
| Build time | 30 min | 30 min |
| Concurrent users | Unlimited (queued) | Unlimited (queued) |
| Duplicate Space rate limit | None | None |

### Model count in one Space

There is **no hard cap** on the number of models in one Space, but practical RAM limits
apply:

| Model size | CPU RAM needed (fp16) | How many fit in 16 GB? |
|---|---|---|
| < 1 B params | ~1–2 GB | ~8 models |
| 1–3 B params | ~2–6 GB | 3–5 models |
| 7 B params | ~14 GB | 1 comfortably (2 with quantisation) |
| 13 B params | ~26 GB | 0 without quantisation |
| 30 B+ params | 60+ GB | Requires 4-bit quant or disk offload |

**Practical guideline:**  
Keep the total unquantised parameter count below ~10 B for a comfortable free-tier Space.
For larger model combinations, use 4-bit BnB quantisation (see Section 5).

### Queue and concurrency

- `demo.queue(max_size=N)` limits how many users can wait — excess requests receive an
  immediate "queue full" error rather than waiting forever.
- Recommended `max_size`: **10–20** for typical GPU demos.
- ZeroGPU serialises GPU access, so even with many queued users only one `@spaces.GPU`
  function runs at a time.

---

## 4. Multi-model loading strategies

### Strategy 1 — Lazy singleton (recommended)

Load each model on first use, cache forever:

```python
from functools import lru_cache

@lru_cache(maxsize=1)
def get_text_model():
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_id = "microsoft/phi-2"
    tok = AutoTokenizer.from_pretrained(model_id)
    mdl = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch.float16, low_cpu_mem_usage=True
    )
    return tok, mdl

@lru_cache(maxsize=1)
def get_image_model():
    from diffusers import StableDiffusionPipeline
    return StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5", torch_dtype=torch.float16
    )
```

The `lru_cache` ensures each model is loaded exactly once regardless of how many
concurrent users trigger the first call (Python's GIL means only one thread initialises
at a time).

### Strategy 2 — Explicit model switcher

If you have more models than fit in RAM simultaneously, implement an explicit switcher
that evicts the current model before loading the next:

```python
_active_model = {"name": None, "obj": None}

def switch_model(name: str):
    if _active_model["name"] == name:
        return _active_model["obj"]
    # Evict current
    if _active_model["obj"] is not None:
        del _active_model["obj"]
        torch.cuda.empty_cache()
        import gc; gc.collect()
    # Load new
    _active_model["obj"] = LOADERS[name]()
    _active_model["name"] = name
    return _active_model["obj"]
```

Expose the switcher via a `gr.Dropdown` so users choose which model to use before
generating.

### Strategy 3 — Background pre-warm with `threading`

For the most frequently-used model, start loading it as a background thread while the UI
initialises:

```python
import threading

def _prewarm():
    try:
        get_text_model()
    except Exception:
        pass   # failure is acceptable; model loads on first real request

threading.Thread(target=_prewarm, daemon=True).start()

with gr.Blocks() as demo:
    ...   # UI is responsive immediately
```

Do **not** pre-warm GPU-heavy models (image/video generation) this way — they consume
RAM needlessly if users only want text generation.

---

## 5. Memory optimisation techniques

### Half-precision

```python
model = Model.from_pretrained("org/model", torch_dtype=torch.float16)
```

Halves memory vs float32 with negligible quality loss for inference.

### 4-bit and 8-bit BitsAndBytes quantisation

```python
from transformers import BitsAndBytesConfig

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-2-7b-chat-hf",
    quantization_config=bnb_config,
    device_map="auto",
)
```

4-bit NF4 typically gives a ~4× memory reduction (7 B → ~4 GB) with ~5% quality
reduction on most benchmarks.

### `device_map="auto"` with CPU offloading

```python
model = AutoModelForCausalLM.from_pretrained(
    "org/large-model",
    torch_dtype=torch.float16,
    device_map="auto",          # splits layers across GPU + CPU automatically
    offload_folder="offload/",  # spill overflow to disk if RAM is tight
    low_cpu_mem_usage=True,
)
```

### Explicit cache clearing

```python
del model
import gc
gc.collect()
torch.cuda.empty_cache()
```

Call this after a model is no longer needed in a session.

---

## 6. UI patterns that feel fast despite GPU cold-starts

ZeroGPU cold-starts (GPU allocation + model `.to("cuda")`) can add 2–10 s of latency
on the first request. These UI patterns make the wait feel shorter:

### Immediate feedback

```python
def start_generation(prompt):
    return gr.update(value="🔄 Requesting GPU…", interactive=False), None

def run_generation(prompt):
    result = generate_image(prompt)   # @spaces.GPU inside
    return gr.update(value="✅ Done", interactive=True), result

generate_btn.click(start_generation, [prompt_box], [status, output_img])
generate_btn.click(run_generation, [prompt_box], [status, output_img])
```

Both `.click` handlers fire at the same time; the first updates the UI instantly, the
second updates it when inference completes.

### Queue position display

```python
with gr.Blocks() as demo:
    gr.HTML('<div id="queue-pos"></div>')

demo.queue(
    status_update_rate=2,   # update every 2 s
    max_size=15,
)
```

Gradio automatically shows queue position in the UI when `demo.queue()` is active — no
extra code needed.

### Progress bars

```python
@spaces.GPU
def generate(prompt, progress=gr.Progress()):
    progress(0, desc="Warming up GPU…")
    pipe = load_pipe().to("cuda")
    progress(0.2, desc="Running…")
    images = pipe(prompt, callback_on_step_end=make_callback(progress, 0.2, 0.9)).images
    progress(1.0, desc="Done!")
    return images[0]

def make_callback(progress, start, end):
    def cb(pipeline, step, timestep, callback_kwargs):
        frac = start + (end - start) * step / pipeline.num_timesteps
        progress(frac)
        return callback_kwargs
    return cb
```

---

## 7. Persistent storage and caching

### Ephemeral disk (free tier)

Files written to `/tmp` or the working directory are lost when the Space restarts.
Use this for in-session caches only.

### Hugging Face Hub model cache

Model weights downloaded via `from_pretrained` are cached in
`~/.cache/huggingface/hub`. This cache **persists across restarts** on paid Spaces with
a persistent disk volume, but **does not** persist on free-tier Spaces.

Workaround for free tier: use `snapshot_download` at startup to ensure the model is
re-downloaded predictably, or rely on the warm-container cache (weights stay in RAM
if the Space has not been idle long enough to be evicted).

### `gr.State` for per-session data

```python
session_data = gr.State({})   # per-user, lives for the browser session

def save_result(result, state):
    state["last_result"] = result
    return state

output_img.change(save_result, [output_img, session_data], [session_data])
```

---

## 8. Debugging and profiling on Spaces

### View logs

In the Space's "Logs" tab on huggingface.co, or via:

```bash
huggingface-cli repo logs <your-space>
```

### Profile GPU usage inside `@spaces.GPU`

```python
@spaces.GPU
def profiled_generate(prompt):
    with torch.profiler.profile(
        activities=[torch.profiler.ProfilerActivity.CUDA],
        record_shapes=True,
    ) as prof:
        result = model(prompt)
    print(prof.key_averages().table(sort_by="cuda_time_total", row_limit=10))
    return result
```

Profiler output goes to the Logs tab.

### Check available GPU memory

```python
@spaces.GPU
def check_mem():
    free, total = torch.cuda.mem_get_info()
    return f"Free: {free/1e9:.1f} GB / Total: {total/1e9:.1f} GB"
```
