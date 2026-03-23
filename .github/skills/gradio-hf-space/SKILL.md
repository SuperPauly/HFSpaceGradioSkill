---
name: gradio-hf-space
description: >
  Expert guide for building production-quality Gradio 6.9.0 apps on HuggingFace Spaces.
  Covers custom components (BunJS + Shadcn), responsive 9:16 / 16:9 unified layouts,
  touchscreen UX (tap / swipe / scroll), async multi-model loading, and the Zero GPU
  decorator. Use this skill whenever the user asks about: Gradio apps, HuggingFace Spaces,
  custom Gradio components, Zero GPU, responsive ML UIs, Gradio layouts, loading models in
  Gradio, Shadcn Gradio components, or BunJS Gradio tooling. Trigger even when the user
  only mentions "gradio", "hf space", "zero gpu", "shadcn gradio", or "responsive ML app".
---

# Gradio & HuggingFace Spaces Skill (Gradio 6.9.0)

This skill helps you build fast, accessible, and visually polished Gradio apps that run well
on HuggingFace Spaces — including GPU-accelerated Spaces with multiple models and
fully custom UI components built with BunJS and Shadcn.

## Table of Contents

1. [Quick-start pattern](#1-quick-start-pattern)
2. [Responsive unified layout (9:16 and 16:9)](#2-responsive-unified-layout-916-and-169)
3. [Touchscreen UX principles](#3-touchscreen-ux-principles)
4. [Custom components — BunJS + Shadcn](#4-custom-components--bunjs--shadcn)
5. [Async model loading without blocking the UI](#5-async-model-loading-without-blocking-the-ui)
6. [Zero GPU decorator and multi-model spaces](#6-zero-gpu-decorator-and-multi-model-spaces)
7. [HuggingFace Spaces limits and best practices](#7-huggingface-spaces-limits-and-best-practices)
8. [UI tricks and performance patterns](#8-ui-tricks-and-performance-patterns)
9. [Reference files](#9-reference-files)
10. [Scripts](#10-scripts)

---

## 1. Quick-start pattern

```python
# app.py  — minimal Gradio 6.9.0 Space skeleton
import gradio as gr

with gr.Blocks(
    theme=gr.themes.Soft(),
    css_paths=["assets/custom.css"],   # optional extra CSS
    title="My Space",
) as demo:
    # See Section 2 for full responsive layout
    gr.Markdown("## My Space")

demo.queue(max_size=20).launch()
```

All the heavy imports (torch, transformers, diffusers …) belong **outside** the `Blocks`
block so the UI loads before models finish initialising — the pattern in Section 5 makes
this non-blocking.

---

## 2. Responsive unified layout (9:16 and 16:9)

Gradio 6.9.0 uses a **12-column CSS grid** via `gr.Row` / `gr.Column(scale=N)`.
You can target both portrait (9:16 — mobile) and landscape (16:9 — desktop/tablet) by
combining Gradio's built-in responsive helpers with a thin CSS override.

### Core layout skeleton

```python
with gr.Blocks(css_paths=["assets/responsive.css"]) as demo:

    # ── Top bar (always full width) ─────────────────────────────────────────
    with gr.Row(elem_id="topbar"):
        gr.Markdown("## 🤗 My Space", elem_classes=["brand"])
        status_badge = gr.HTML("<span id='status'>Loading…</span>")

    # ── Main content area ────────────────────────────────────────────────────
    with gr.Row(elem_id="main-row", equal_height=True):

        # Left panel — input controls (collapses on portrait / 9:16)
        with gr.Column(scale=4, min_width=280, elem_id="input-panel"):
            prompt_box = gr.Textbox(
                label="Prompt",
                lines=4,
                placeholder="Describe your image…",
                elem_id="prompt",
            )
            run_btn = gr.Button("Generate", variant="primary", size="lg")

        # Right / main panel — outputs (always visible)
        with gr.Column(scale=8, elem_id="output-panel"):
            output_image = gr.Image(
                label="Output",
                show_download_button=True,
                elem_id="result-img",
            )

    # ── Footer ──────────────────────────────────────────────────────────────
    with gr.Row(elem_id="footer"):
        gr.Markdown("Powered by Gradio 6.9.0 · HuggingFace Spaces")
```

### `assets/responsive.css` — CSS breakpoint overrides

```css
/* ── 16:9 (landscape ≥ 900 px) — side-by-side ── */
@media (min-width: 900px) {
  #main-row { flex-direction: row !important; }
  #input-panel { max-width: 360px; }
}

/* ── 9:16 (portrait < 600 px) — stacked ── */
@media (max-width: 599px) {
  #main-row { flex-direction: column !important; }
  #input-panel { width: 100% !important; max-width: 100%; }
  #output-panel { width: 100% !important; }
  /* Larger tap targets */
  button, .gr-button { min-height: 48px !important; font-size: 1.1rem !important; }
  textarea, input[type="text"] { font-size: 16px !important; } /* prevents iOS zoom */
}

/* ── Tablet mid-range (600 – 899 px) ── */
@media (min-width: 600px) and (max-width: 899px) {
  #main-row { flex-direction: column !important; }
  #input-panel { width: 100% !important; }
}
```

### Why this matters

- Gradio renders inside a single `<div id="root">` so standard CSS media queries work
  reliably.
- Setting `min_width` on a `Column` prevents it from shrinking below a usable size.
- Avoid fixed pixel heights on output components; let images and videos auto-size so they
  reflow correctly on small screens.

---

## 3. Touchscreen UX principles

Good ML UIs on touch devices need deliberate attention to three input modes:

### Tap

- Use `size="lg"` on every `gr.Button` so tap targets are ≥ 48 × 48 px (WCAG 2.5.5).
- Place the primary action button at the **bottom** of the input panel on portrait layouts —
  the thumb's natural reach zone.
- Use `gr.Dropdown` and `gr.Radio` with enough vertical spacing; the default Gradio
  `gr.Dropdown` already meets tap-target requirements on most themes.

### Swipe / scroll

- Prefer `gr.Tab` for mode-switching rather than deeply nested accordions — swipe-to-switch
  is naturally discoverable on mobile.
- Keep the page shallow (avoid very long scroll distance) by using `gr.Accordion` to
  collapse advanced settings.
- On the output side, use `gr.Gallery` rather than stacked images — it provides a
  horizontal swipe strip on touch devices.

### Keyboard and mouse (desktop)

- Wire `every` on `gr.Textbox` for live-preview at low cost, or `submit` to trigger on
  Enter (reduces accidental submits on mobile).
- Provide keyboard shortcuts via `gr.on("key_up", …)` for power users.
- Use `gr.Slider` with `info=` text so mouse users see value context without a tooltip.

### Example: touch-optimised gallery

```python
with gr.Row():
    gallery = gr.Gallery(
        label="Results",
        columns=2,          # 2-up on portrait, increases automatically on wider screens
        rows=2,
        object_fit="cover",
        height="auto",
        elem_id="results-gallery",
    )
```

---

## 4. Custom components — BunJS + Shadcn

Gradio 6.9.0 ships a first-class custom component system. The frontend is authored in
**Svelte 5** (bundled by Gradio's own toolchain, which uses **Bun** as the package
manager) and you can freely import Shadcn-Svelte (the official Svelte port of Shadcn/UI)
plus any Shadcn third-party extension.

> **Full reference:** `references/gradio-6.9-custom-components.md`

### Scaffold a new component

```bash
# Requires Python ≥ 3.10 and Bun installed
gradio cc create MySlider --template slider

# The scaffold produces:
# my_slider/
# ├── backend/my_slider/     ← Python component class
# ├── frontend/              ← Svelte + Bun workspace
# │   ├── package.json       ← Bun project (uses bun.lockb)
# │   ├── src/
# │   │   ├── Index.svelte   ← exported component
# │   │   └── lib/           ← sub-components
# └── demo/app.py            ← live dev demo
```

Or use the bundled scaffold script:

```bash
python .github/skills/gradio-hf-space/scripts/scaffold_custom_component.py \
  --name my-rating \
  --template slider \
  --shadcn        # installs shadcn-svelte and a starter component
```

### Adding Shadcn to the frontend

```bash
cd my_slider/frontend
bun add shadcn-svelte        # core Shadcn Svelte
bun add @shadcn-svelte/ui    # pre-built component registry (optional convenience package)
```

In `src/Index.svelte`:

```svelte
<script lang="ts">
  import { Slider } from "shadcn-svelte";   // Shadcn Svelte slider
  import type { Gradio } from "@gradio/utils";

  export let gradio: Gradio<{ change: never }>;
  export let value: number = 50;
  export let label: string = "";

  function dispatch(v: number) {
    value = v;
    gradio.dispatch("change");
  }
</script>

<label class="text-sm font-medium">{label}</label>
<Slider
  bind:value
  min={0} max={100} step={1}
  onValueChange={(v) => dispatch(v[0])}
/>
```

### Third-party Shadcn components

The Shadcn/UI ecosystem has community extensions that port Radix primitives. Useful ones
for ML UIs:

| Package | What it adds |
|---|---|
| `shadcn-svelte-extra` | Combobox, multi-select, date-range picker |
| `@shadcn-svelte/charts` | Recharts-backed bar/line/area charts |
| `@huntabyte/primitives` | Drawer, Context menu |

Install and import exactly like core Shadcn components.

### Dev loop

```bash
cd my_slider
gradio cc dev   # hot-reload with Bun, opens browser on port 7860
```

After you're happy:

```bash
gradio cc build          # produces dist/
pip install -e .         # use locally
gradio cc publish        # push to HuggingFace Hub as a package
```

### Layout patterns with custom components

Custom components return Svelte components, which respect Gradio's grid system via
`elem_classes`. Use Tailwind utility classes (Gradio includes Tailwind by default) to add
responsive padding and max-widths inside the component:

```svelte
<div class="w-full max-w-md mx-auto p-4 sm:p-2">
  <!-- component body -->
</div>
```

---

## 5. Async model loading without blocking the UI

The key principle: **initialise every model lazily**, gated behind the first real request
that needs it. This keeps startup time under 2 s even with many potential models.

### Pattern A — `asyncio` with `concurrent.futures`

```python
import asyncio, gradio as gr
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

_executor = ThreadPoolExecutor(max_workers=2)

@lru_cache(maxsize=1)
def get_text_model():
    from transformers import pipeline
    return pipeline("text-generation", model="gpt2")

@lru_cache(maxsize=1)
def get_image_model():
    from diffusers import StableDiffusionPipeline
    import torch
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5", torch_dtype=torch.float16
    )
    return pipe.to("cuda")

async def run_text(prompt: str):
    loop = asyncio.get_event_loop()
    # Load lazily in thread pool — does not block the Gradio event loop
    model = await loop.run_in_executor(_executor, get_text_model)
    return model(prompt, max_new_tokens=100)[0]["generated_text"]

async def run_image(prompt: str):
    loop = asyncio.get_event_loop()
    model = await loop.run_in_executor(_executor, get_image_model)
    result = await loop.run_in_executor(_executor, lambda: model(prompt).images[0])
    return result
```

### Pattern B — `gr.State` loading indicator

Show the user that a model is warming up without blocking the whole app:

```python
def generate_with_status(prompt, progress=gr.Progress()):
    progress(0, desc="Loading model…")
    model = get_image_model()          # cached after first call
    progress(0.3, desc="Running inference…")
    result = model(prompt).images[0]
    progress(1.0, desc="Done")
    return result
```

### Pattern C — background pre-warm (optional)

If you know users will almost certainly hit a model, pre-warm it in the background while
the UI loads. This trades a bit of VRAM for faster first-inference:

```python
import threading

def _prewarm():
    get_text_model()   # populate the lru_cache in background

threading.Thread(target=_prewarm, daemon=True).start()

with gr.Blocks() as demo:
    ...   # UI ready immediately; model loads concurrently
```

---

## 6. Zero GPU decorator and multi-model spaces

> **Full reference:** `references/hf-spaces-zerogpu.md`

### What Zero GPU is

HuggingFace Spaces "Zero GPU" provides shared GPU access without paying for a dedicated
GPU instance. GPUs are allocated on-demand per function call and released automatically
when the function returns.

### Applying the decorator

```python
import spaces          # provided by the HF Zero GPU runtime
import gradio as gr

@spaces.GPU(duration=60)   # max seconds this fn may hold the GPU; default 60
def generate(prompt: str) -> str:
    # Everything inside here runs with a real CUDA device available.
    # Outside this function, torch.cuda.is_available() may return False.
    model = get_model()
    return model(prompt)
```

Key rules:
- The `@spaces.GPU` decorator must wrap the innermost function, not the entire app.
- Models must be **loaded inside or before** `@spaces.GPU` function calls. Loading a model
  *outside* on the CPU and then moving it to CUDA *inside* the decorated function is the
  recommended pattern.
- Do **not** wrap UI helpers (formatters, validators) in `@spaces.GPU` — allocating a GPU
  for non-GPU work wastes quota.

### Loading multiple models without blocking

```python
from functools import lru_cache
import spaces, torch

@lru_cache(maxsize=1)
def load_sd():
    from diffusers import StableDiffusionPipeline
    pipe = StableDiffusionPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        torch_dtype=torch.float16,
    )
    return pipe   # stays on CPU until .to("cuda") is called inside @spaces.GPU

@spaces.GPU(duration=90)
def run_sd(prompt: str):
    pipe = load_sd().to("cuda")
    return pipe(prompt).images[0]

@lru_cache(maxsize=1)
def load_whisper():
    import whisper
    return whisper.load_model("base")

@spaces.GPU(duration=30)
def run_whisper(audio_path: str):
    model = load_whisper()
    # whisper handles device selection internally
    return model.transcribe(audio_path)["text"]
```

This pattern means:
- Models live in CPU RAM between calls (free during idle).
- GPU memory is only used during the decorated function's execution window.
- Multiple models can co-exist in one Space because they are never all on GPU simultaneously.

---

## 7. HuggingFace Spaces limits and best practices

> **Full reference:** `references/hf-spaces-zerogpu.md` (Section 3)

### Hard limits (Zero GPU tier, as of 2025)

| Resource | Limit |
|---|---|
| GPU allocation time per call | 60 s default, up to 180 s with `duration=` |
| Concurrent GPU users | ~1 (queue serialises) |
| Disk space | 50 GB (persistent `/data` with paid tier, ephemeral otherwise) |
| RAM | ~16 GB (varies by hardware tier) |
| Total models in one Space | No hard cap, but practical limit is **3–4 large models** (7B+) before CPU RAM is exhausted |
| HF Hub model downloads | Cached in `/root/.cache/huggingface`; counts against disk quota |

### Practical model count

- **1–2 large models (≥ 7B params):** comfortable, all fits in 16 GB RAM.
- **3–4 medium models (1–3 B):** feasible with lazy loading; never load all at once.
- **5+ models:** requires careful memory management (`offload_state_dict`, `disk_offload`)
  or splitting across multiple Spaces behind a router.

### Staying within limits

1. **Use `torch.float16` or `bfloat16`** — halves VRAM vs float32.
2. **`del model; torch.cuda.empty_cache()`** between inferences if you must load
   multiple large models sequentially.
3. **Quantize with `bitsandbytes`** — 4-bit or 8-bit quantization typically gives a
   3–4× memory reduction with minimal quality loss.
4. **Pin the most-used model** and load others on demand.
5. **Set `low_cpu_mem_usage=True`** in `from_pretrained` — avoids double-buffering during
   load.

---

## 8. UI tricks and performance patterns

### Streaming outputs

```python
def stream_text(prompt):
    model = get_text_model()
    streamer = TextIteratorStreamer(model.tokenizer)
    # run in thread so we can yield tokens as they arrive
    thread = threading.Thread(target=model, kwargs={"text_inputs": prompt, "streamer": streamer})
    thread.start()
    generated = ""
    for token in streamer:
        generated += token
        yield generated

output = gr.Textbox(label="Response")
run_btn.click(stream_text, inputs=[prompt_box], outputs=[output])
```

### Debounced live preview

```python
prompt_box.change(
    fn=run_preview,
    inputs=[prompt_box],
    outputs=[preview_img],
    show_progress="hidden",
    trigger_mode="once",   # prevents queue flood on fast typing
)
```

### Optimistic UI with `gr.State`

Update the UI immediately with placeholder content, then swap in the real result:

```python
def optimistic_start(prompt):
    return gr.update(value="⏳ Generating…", interactive=False), None

def real_generate(prompt):
    return gr.update(interactive=True), run_image_model(prompt)

generate_btn.click(optimistic_start, [prompt_box], [status_text, output_img])
generate_btn.click(real_generate, [prompt_box], [status_text, output_img])
```

### `gr.on` for multiple triggers

Avoid repeating `.click(fn, …)` and `.submit(fn, …)`. Use:

```python
gr.on(
    triggers=[run_btn.click, prompt_box.submit],
    fn=generate,
    inputs=[prompt_box, model_selector],
    outputs=[output_img],
)
```

### Caching with `gr.State` and `functools.lru_cache`

```python
# Per-session cache so each user gets independent state
session_history = gr.State([])

def add_to_history(new_item, history):
    history = history + [new_item]
    return history, history   # return updated state + display

run_btn.click(add_to_history, [output_img, session_history], [session_history, gallery])
```

### Avoiding Gradio re-render thrash

- Use `gr.update()` rather than returning full component objects — Gradio only patches
  changed properties.
- Batch related updates into a single function return tuple instead of chaining multiple
  events.
- Use `queue=False` on very fast non-GPU callbacks (e.g., tab switches, local formatters)
  to bypass the queue overhead.

---

## 9. Reference files

| File | When to read |
|---|---|
| `references/gradio-6.9-custom-components.md` | Building or modifying a custom Gradio component |
| `references/hf-spaces-zerogpu.md` | Zero GPU, multi-model loading, HF Spaces limits |
| `references/responsive-layout.md` | Responsive CSS, 9:16/16:9 layout patterns, touch UX details |

Read only the reference file(s) relevant to the current task.

---

## 10. Scripts

| Script | Usage |
|---|---|
| `scripts/scaffold_custom_component.py` | Scaffold a new Gradio custom component with BunJS + optional Shadcn |
| `scripts/demo_app.py` | Full reference Gradio 6.9.0 app demonstrating all patterns in this skill |

Run any script with `--help` for usage details.
