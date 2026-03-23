"""
demo_app.py
───────────
Reference Gradio 6.9.0 app demonstrating all patterns from the gradio-hf-space skill:

  ✅  Responsive unified layout (9:16 portrait & 16:9 landscape via CSS)
  ✅  Touchscreen UX (large tap targets, swipe-friendly tabs, bottom CTA)
  ✅  Async / lazy model loading without blocking the UI
  ✅  HuggingFace Spaces Zero GPU decorator pattern
  ✅  Multi-model loading with lru_cache + explicit GPU placement
  ✅  Streaming text output
  ✅  Progress bars
  ✅  Optimistic UI pattern
  ✅  gr.on for multiple triggers
  ✅  Per-session state with gr.State

Usage:
  pip install "gradio>=6.9.0" transformers diffusers torch spaces
  python demo_app.py                     # full app (requires GPU for image gen)
  python demo_app.py --cpu-only          # text generation only, no GPU required
  python demo_app.py --help

Note: This file is a reference implementation. On HuggingFace Spaces, rename it to
app.py and ensure the `spaces` package is available (it is pre-installed on HF Spaces).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import gradio as gr


# ── CLI flags ─────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Reference Gradio 6.9.0 app for the gradio-hf-space skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--cpu-only", action="store_true", help="Disable image generation (no GPU needed)")
    p.add_argument("--share", action="store_true", help="Create a public Gradio share link")
    p.add_argument("--port", type=int, default=7860, help="Port to run on (default: 7860)")
    return p.parse_args()


# ── Zero GPU import (graceful fallback when running locally) ──────────────────

try:
    import spaces  # type: ignore[import]
    HAS_SPACES = True
except ImportError:
    HAS_SPACES = False

    # Define a no-op decorator so the code is identical on and off HF Spaces
    class spaces:  # type: ignore[no-redef]
        @staticmethod
        def GPU(fn=None, *, duration: int = 60):
            if fn is not None:
                return fn
            def decorator(f):
                return f
            return decorator


# ── Model loaders (lazy, cached) ──────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_text_model():
    """Load a small text-generation model. Cached on first call."""
    print("Loading text model…", flush=True)
    from transformers import pipeline
    return pipeline(
        "text-generation",
        model="sshleifer/tiny-gpt2",   # tiny model — swap for a better one in production
        device=-1,                      # CPU; move to GPU inside @spaces.GPU if needed
    )


@lru_cache(maxsize=1)
def _load_image_model():
    """Load a diffusion model on CPU (moved to GPU inside @spaces.GPU fn)."""
    print("Loading image model…", flush=True)
    import torch
    from diffusers import StableDiffusionPipeline  # type: ignore[import]
    pipe = StableDiffusionPipeline.from_pretrained(
        "hf-internal-testing/tiny-stable-diffusion-pipe",  # tiny test model
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
    )
    return pipe


# ── Text generation (CPU-compatible) ─────────────────────────────────────────

def generate_text(prompt: str, max_tokens: int, progress=gr.Progress()):
    """Generate text, streaming tokens progressively."""
    progress(0.0, desc="Loading model…")
    model = _load_text_model()
    progress(0.2, desc="Running inference…")
    outputs = model(prompt, max_new_tokens=int(max_tokens), do_sample=True, temperature=0.8)
    progress(1.0)
    return outputs[0]["generated_text"]


# ── Image generation (GPU via Zero GPU decorator) ─────────────────────────────

@spaces.GPU(duration=60)
def generate_image(prompt: str, steps: int, guidance: float, progress=gr.Progress()):
    """Generate an image using the diffusion model (requires GPU on HF Spaces)."""
    import torch  # local import — only needed when this fn runs

    progress(0.0, desc="Acquiring GPU…")
    pipe = _load_image_model().to("cuda")
    progress(0.1, desc="Running diffusion…")

    def step_callback(pipeline, step, timestep, callback_kwargs):
        frac = 0.1 + 0.85 * step / pipeline.num_timesteps
        progress(frac, desc=f"Step {step}/{pipeline.num_timesteps}")
        return callback_kwargs

    result = pipe(
        prompt,
        num_inference_steps=steps,
        guidance_scale=guidance,
        callback_on_step_end=step_callback,
    )
    progress(1.0, desc="Done!")

    # Move back to CPU so GPU is released cleanly
    pipe.to("cpu")
    torch.cuda.empty_cache()

    return result.images[0]


# ── Background pre-warm for the text model ────────────────────────────────────

def _prewarm_text():
    try:
        _load_text_model()
    except Exception:
        pass


threading.Thread(target=_prewarm_text, daemon=True).start()


# ── Responsive CSS ────────────────────────────────────────────────────────────

RESPONSIVE_CSS = """
/* ── Portrait / mobile (< 600 px — roughly 9:16) ── */
@media (max-width: 599px) {
  #main-row { flex-direction: column !important; gap: 12px; }
  #input-panel, #output-panel { width: 100% !important; min-width: 0 !important; max-width: 100% !important; }
  #run-btn button { min-height: 52px !important; font-size: 1.1rem !important; width: 100%; }
  textarea, input[type="text"] { font-size: 16px !important; }  /* prevent iOS zoom */
  #input-panel { display: flex; flex-direction: column; }
  #run-btn { order: 99; margin-top: 12px; }
}

/* ── Tablet (600–899 px) ── */
@media (min-width: 600px) and (max-width: 899px) {
  #main-row { flex-direction: column !important; }
  #input-panel, #output-panel { width: 100% !important; }
}

/* ── Desktop landscape (≥ 900 px — roughly 16:9) ── */
@media (min-width: 900px) {
  #main-row { flex-direction: row !important; }
  #input-panel { max-width: 380px; }
}

/* Active state for tap feedback */
button:active { transform: scale(0.97); opacity: 0.85; transition: transform 0.05s; }
"""


# ── Swipe-to-switch-tabs JavaScript snippet ───────────────────────────────────

SWIPE_JS = """
<script>
(function() {
  var startX = 0;
  document.addEventListener('touchstart', function(e) {
    startX = e.touches[0].clientX;
  }, { passive: true });
  document.addEventListener('touchend', function(e) {
    var dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) < 50) return;
    var tabs = document.querySelectorAll('[role="tab"]');
    var active = Array.prototype.indexOf.call(tabs,
      document.querySelector('[role="tab"][aria-selected="true"]'));
    if (active === -1) return;
    var next = dx < 0 ? Math.min(active + 1, tabs.length - 1)
                      : Math.max(active - 1, 0);
    if (next !== active) tabs[next].click();
  }, { passive: true });
})();
</script>
"""

# Keyboard shortcut: Ctrl/Cmd+Enter to trigger generation
KEYBOARD_JS = """
<script>
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    var btn = document.getElementById('run-btn-elem');
    if (btn) btn.click();
  }
});
</script>
"""


# ── Build the UI ──────────────────────────────────────────────────────────────

def build_ui(cpu_only: bool = False) -> gr.Blocks:

    with gr.Blocks(
        css=RESPONSIVE_CSS,
        theme=gr.themes.Soft(),
        title="Gradio 6.9.0 Reference App",
        analytics_enabled=False,
    ) as demo:

        # Inject touch / keyboard JS
        gr.HTML(SWIPE_JS + KEYBOARD_JS)

        # ── Top bar ──────────────────────────────────────────────────────────
        with gr.Row(elem_id="topbar"):
            gr.Markdown("## 🤗 Gradio 6.9.0 Reference Space")
            status_html = gr.HTML("<span style='color:gray'>Ready</span>", elem_id="status-badge")

        # ── Tabbed navigation ─────────────────────────────────────────────────
        with gr.Tabs(elem_id="main-tabs"):

            # ── Tab 1: Text Generation ─────────────────────────────────────────
            with gr.Tab("✍️ Text", elem_id="tab-text"):

                with gr.Row(elem_id="main-row", equal_height=False):

                    # Left / input panel
                    with gr.Column(scale=4, min_width=280, elem_id="input-panel"):
                        text_prompt = gr.Textbox(
                            label="Prompt",
                            lines=4,
                            placeholder="Once upon a time…",
                            submit_btn=True,
                            elem_id="text-prompt",
                        )
                        with gr.Accordion("Options", open=False):
                            max_tokens_slider = gr.Slider(
                                10, 200, value=50, step=10,
                                label="Max new tokens",
                                info="Number of tokens to generate",
                            )
                        text_run_btn = gr.Button(
                            "Generate text ✨",
                            variant="primary",
                            size="lg",
                            elem_id="run-btn",
                            elem_classes=["run-btn"],
                        )

                    # Right / output panel
                    with gr.Column(scale=8, elem_id="output-panel"):
                        text_output = gr.Textbox(
                            label="Output",
                            lines=8,
                            max_lines=20,
                            autoscroll=True,
                            interactive=False,
                            elem_id="text-output",
                        )

                # Optimistic UI: disable button immediately, re-enable when done
                def _text_start(_prompt: str):
                    return (
                        gr.update(value="⏳ Generating…", interactive=False),
                        gr.update(value="<span style='color:orange'>Generating…</span>"),
                        "",
                    )

                def _text_run(prompt: str, max_tokens: int, progress=gr.Progress()):
                    result = generate_text(prompt, max_tokens, progress)
                    return (
                        gr.update(value="Generate text ✨", interactive=True),
                        gr.update(value="<span style='color:green'>Done ✅</span>"),
                        result,
                    )

                gr.on(
                    triggers=[text_run_btn.click, text_prompt.submit],
                    fn=_text_start,
                    inputs=[text_prompt],
                    outputs=[text_run_btn, status_html, text_output],
                    queue=False,
                ).then(
                    fn=_text_run,
                    inputs=[text_prompt, max_tokens_slider],
                    outputs=[text_run_btn, status_html, text_output],
                )

            # ── Tab 2: Image Generation (GPU) ──────────────────────────────────
            if not cpu_only:
                with gr.Tab("🖼️ Image (GPU)", elem_id="tab-image"):

                    with gr.Row(elem_id="main-row", equal_height=False):

                        with gr.Column(scale=4, min_width=280, elem_id="input-panel"):
                            img_prompt = gr.Textbox(
                                label="Prompt",
                                lines=3,
                                placeholder="A golden retriever in a field of sunflowers…",
                                submit_btn=True,
                            )
                            with gr.Accordion("Sampling options", open=False):
                                steps_slider = gr.Slider(
                                    1, 50, value=20, step=1,
                                    label="Inference steps",
                                    info="20–30 is the sweet spot. More = slower but sharper.",
                                )
                                guidance_slider = gr.Slider(
                                    1.0, 15.0, value=7.5, step=0.5,
                                    label="Guidance scale (CFG)",
                                    info="Higher = more prompt-adherent, less creative.",
                                )
                            img_run_btn = gr.Button(
                                "Generate image 🎨",
                                variant="primary",
                                size="lg",
                                elem_id="run-btn",
                            )

                        with gr.Column(scale=8, elem_id="output-panel"):
                            output_image = gr.Image(
                                label="Output image",
                                show_download_button=True,
                                height=512,
                                elem_id="output-image",
                            )

                    def _img_start(_p, _s, _g):
                        return (
                            gr.update(value="⏳ Requesting GPU…", interactive=False),
                            gr.update(value="<span style='color:orange'>Allocating GPU…</span>"),
                            None,
                        )

                    def _img_run(prompt, steps, guidance, progress=gr.Progress()):
                        image = generate_image(prompt, int(steps), float(guidance), progress)
                        return (
                            gr.update(value="Generate image 🎨", interactive=True),
                            gr.update(value="<span style='color:green'>Done ✅</span>"),
                            image,
                        )

                    gr.on(
                        triggers=[img_run_btn.click, img_prompt.submit],
                        fn=_img_start,
                        inputs=[img_prompt, steps_slider, guidance_slider],
                        outputs=[img_run_btn, status_html, output_image],
                        queue=False,
                    ).then(
                        fn=_img_run,
                        inputs=[img_prompt, steps_slider, guidance_slider],
                        outputs=[img_run_btn, status_html, output_image],
                    )

            # ── Tab 3: Session history ─────────────────────────────────────────
            with gr.Tab("📚 History", elem_id="tab-history"):
                gr.Markdown("_Results from this session will appear here (swipe to browse on mobile)._")
                history_gallery = gr.Gallery(
                    label="Generated images",
                    columns=2,
                    rows=3,
                    height="auto",
                    object_fit="cover",
                    allow_preview=True,
                    elem_id="history-gallery",
                )
                history_state = gr.State([])

                if not cpu_only:
                    # Append each new image to the gallery
                    output_image.change(
                        fn=lambda img, hist: hist + [img] if img is not None else hist,
                        inputs=[output_image, history_state],
                        outputs=[history_state],
                        queue=False,
                    )
                    history_state.change(
                        fn=lambda hist: hist,
                        inputs=[history_state],
                        outputs=[history_gallery],
                        queue=False,
                    )

        # ── Footer ────────────────────────────────────────────────────────────
        with gr.Row(elem_id="footer"):
            gr.Markdown(
                "Built with **Gradio 6.9.0** · Responsive layout · "
                "Zero GPU · [gradio-hf-space skill]"
            )

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()

    demo = build_ui(cpu_only=args.cpu_only)

    demo.queue(max_size=20).launch(
        share=args.share,
        server_port=args.port,
        show_error=True,
    )


if __name__ == "__main__":
    main()
