# Responsive Layout & Touchscreen UX for Gradio 6.9.0

## Table of Contents

1. [Layout philosophy](#1-layout-philosophy)
2. [Gradio 6.9.0 grid system](#2-gradio-690-grid-system)
3. [9:16 portrait layout (mobile)](#3-916-portrait-layout-mobile)
4. [16:9 landscape layout (desktop)](#4-169-landscape-layout-desktop)
5. [Unified responsive layout (single codebase)](#5-unified-responsive-layout-single-codebase)
6. [Touch input — tap](#6-touch-input--tap)
7. [Touch input — swipe](#7-touch-input--swipe)
8. [Touch input — scroll and drag](#8-touch-input--scroll-and-drag)
9. [Keyboard and mouse enhancements](#9-keyboard-and-mouse-enhancements)
10. [Accessibility considerations](#10-accessibility-considerations)
11. [Testing on real devices](#11-testing-on-real-devices)

---

## 1. Layout philosophy

A well-designed ML demo UI should satisfy three constraints simultaneously:

1. **Legible controls on a 375 px phone screen** (9:16 portrait).
2. **Efficient use of horizontal space on a 1440 px desktop** (16:9 landscape).
3. **Zero code duplication** — one `app.py` serves both.

The strategy: use Gradio's row/column system for structural layout, then use CSS media
queries (injected via `css_paths=`) to reflow the layout at breakpoints. Custom components
written with Svelte + Tailwind handle their own internal responsiveness.

---

## 2. Gradio 6.9.0 grid system

Gradio uses a **12-column flexbox grid**:

```
gr.Row            → flex container (row direction by default)
  gr.Column(scale=N)  → flex child; N is relative weight (not absolute columns)
```

Key properties:

| Property | Type | Effect |
|---|---|---|
| `scale` | int | Relative width within a `gr.Row`. `scale=4` + `scale=8` = 1:2 ratio |
| `min_width` | int (px) | Prevent column shrinking below this width |
| `elem_id` | str | CSS ID for targeting with custom CSS |
| `elem_classes` | list[str] | CSS classes for bulk styling |
| `equal_height` | bool (Row) | Stretch all children to equal height |
| `variant` | "default"\|"panel"\|"compact" | Visual card styling |

When columns exceed the container width (because `min_width` kicks in), they automatically
wrap to a new row — this is how you get "stacking" on small screens without JavaScript.

---

## 3. 9:16 portrait layout (mobile)

Design principles for portrait / phone:

- **Single column** — stack everything vertically.
- **Full-width inputs** — no side-by-side inputs.
- **Large tap targets** — 48 × 48 px minimum (WCAG 2.5.5).
- **Primary action at the bottom** — thumb's natural reach zone.
- **Minimal scroll depth** — collapse advanced options behind `gr.Accordion`.

```python
with gr.Blocks(css_paths=["assets/responsive.css"]) as demo:

    # ── Header ──
    gr.Markdown("## 🤗 My Space", elem_classes=["page-header"])

    # ── Tabbed navigation (swipe-friendly) ──
    with gr.Tabs(elem_id="main-tabs"):

        with gr.Tab("Generate", elem_id="tab-generate"):

            # Input area (stacks on portrait)
            with gr.Column(elem_id="input-col"):
                prompt_box = gr.Textbox(
                    label="Prompt",
                    lines=3,
                    placeholder="Describe your image…",
                    submit_btn=True,       # shows ⏎ button — good for mobile keyboards
                    elem_id="prompt-input",
                )
                with gr.Accordion("Advanced", open=False, elem_id="advanced-accordion"):
                    steps_slider = gr.Slider(1, 50, value=20, label="Steps")
                    guidance_slider = gr.Slider(1.0, 15.0, value=7.5, step=0.5, label="Guidance scale")
                run_btn = gr.Button("Generate ✨", variant="primary", size="lg", elem_id="run-btn")

            # Output area
            output_img = gr.Image(
                label="Output",
                show_download_button=True,
                elem_id="output-img",
            )

        with gr.Tab("History"):
            gallery = gr.Gallery(columns=2, rows=3, height="auto", elem_id="history-gallery")
```

---

## 4. 16:9 landscape layout (desktop)

Design principles for landscape / desktop:

- **Two-column** — inputs left, output right.
- **Persistent sidebar** — controls always visible without scrolling.
- **Denser information density** — more can fit on screen.
- **Hover states and tooltips** — not available on touch; fine to use on desktop.

```python
with gr.Row(elem_id="main-row", equal_height=True):

    # Left sidebar (input controls)
    with gr.Column(scale=3, min_width=300, elem_id="sidebar"):
        prompt_box = gr.Textbox(label="Prompt", lines=5, elem_id="prompt-input")
        model_picker = gr.Dropdown(
            ["SD 1.5", "SD XL", "FLUX"],
            value="SD 1.5",
            label="Model",
            info="FLUX is slower but higher quality",
        )
        with gr.Row():
            steps_slider = gr.Slider(1, 50, value=20, label="Steps", scale=1)
            guidance_slider = gr.Slider(1.0, 15.0, value=7.5, step=0.5, label="CFG", scale=1)
        run_btn = gr.Button("Generate", variant="primary", size="lg")

    # Main content area (output)
    with gr.Column(scale=9, elem_id="main-content"):
        output_img = gr.Image(
            label="Output",
            show_download_button=True,
            height=512,
            elem_id="output-img",
        )
        with gr.Row():
            gallery = gr.Gallery(
                label="History",
                columns=4,
                rows=1,
                height=128,
                elem_id="history-strip",
            )
```

---

## 5. Unified responsive layout (single codebase)

The key is to write the layout once and use CSS media queries to reflow it:

```python
# app.py
with gr.Blocks(
    css_paths=["assets/responsive.css"],
    theme=gr.themes.Soft(),
) as demo:

    with gr.Row(elem_id="main-row", equal_height=False):

        with gr.Column(
            scale=4,
            min_width=280,     # triggers wrap/stack on narrow screens
            elem_id="input-panel",
        ):
            prompt_box = gr.Textbox(
                label="Prompt",
                lines=4,
                submit_btn=True,
                elem_id="prompt-input",
            )
            with gr.Accordion("Advanced", open=False):
                steps_slider = gr.Slider(1, 50, value=20, label="Steps")
            run_btn = gr.Button("Generate", variant="primary", size="lg", elem_id="run-btn")

        with gr.Column(scale=8, elem_id="output-panel"):
            output_img = gr.Image(
                label="Output",
                show_download_button=True,
                elem_id="output-img",
            )
```

`assets/responsive.css`:

```css
/* ── Base styles ── */
#run-btn { width: 100%; }

/* ── Portrait / mobile (< 600 px, roughly 9:16) ── */
@media (max-width: 599px) {
  /* Stack the two panels vertically */
  #main-row {
    flex-direction: column !important;
    gap: 12px;
  }
  #input-panel,
  #output-panel {
    width: 100% !important;
    min-width: 0 !important;
    max-width: 100% !important;
  }

  /* Larger tap targets */
  button.lg,
  .gr-button {
    min-height: 52px !important;
    font-size: 1.1rem !important;
  }

  /* Prevent iOS auto-zoom on focus */
  input[type="text"],
  textarea {
    font-size: 16px !important;
  }

  /* Move primary action to bottom of input panel */
  #input-panel {
    display: flex;
    flex-direction: column;
  }
  #run-btn {
    order: 99;          /* push to end of flex container */
    margin-top: 12px;
  }
}

/* ── Tablet mid-range (600–899 px) ── */
@media (min-width: 600px) and (max-width: 899px) {
  #main-row { flex-direction: column !important; }
  #input-panel { width: 100% !important; }
  #output-panel { width: 100% !important; }
}

/* ── Landscape / desktop (≥ 900 px, roughly 16:9) ── */
@media (min-width: 900px) {
  #main-row { flex-direction: row !important; }
  #input-panel { max-width: 380px; }
}
```

---

## 6. Touch input — tap

### Minimum tap target size

The Web Content Accessibility Guidelines (WCAG 2.5.5) specify 44 × 44 CSS pixels. Apple's
HIG recommends 44 pt (≈ 48 px on most devices). Aim for **48 × 48 px**.

Gradio's `size="lg"` buttons already meet this, but custom or unstyled elements need
explicit sizing:

```css
.custom-icon-btn {
  min-width: 48px;
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

### Spacing between tap targets

Adjacent tap targets should have at least **8 px** of padding/margin between them to
prevent accidental taps:

```css
.gr-radio-label,
.gr-checkbox-label {
  padding: 12px 16px !important;   /* generous touch padding */
  margin-bottom: 4px !important;
}
```

### Visual feedback on tap

Add an active state so the user knows the tap was registered:

```css
button:active,
.tap-target:active {
  transform: scale(0.97);
  opacity: 0.85;
  transition: transform 0.05s, opacity 0.05s;
}
```

---

## 7. Touch input — swipe

### `gr.Tab` swipe navigation

Gradio's `gr.Tabs` does not natively support swipe-to-switch, but you can add it via
a lightweight JavaScript snippet injected in `gr.HTML`:

```python
gr.HTML("""
<script>
(function() {
  let startX = 0;
  document.addEventListener('touchstart', e => { startX = e.touches[0].clientX; }, { passive: true });
  document.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) < 50) return;
    const tabs = document.querySelectorAll('[role="tab"]');
    const active = Array.from(tabs).findIndex(t => t.getAttribute('aria-selected') === 'true');
    const next = dx < 0
      ? Math.min(active + 1, tabs.length - 1)
      : Math.max(active - 1, 0);
    if (next !== active) tabs[next].click();
  }, { passive: true });
})();
</script>
""")
```

### `gr.Gallery` horizontal swipe

`gr.Gallery` renders a grid that the user can scroll through. On mobile, users expect
horizontal swipe for image browsing. Set `columns=1` and `height="auto"` on portrait to
present a card-stack that pans horizontally:

```python
gallery = gr.Gallery(
    columns=1,
    rows=1,
    height="auto",
    object_fit="contain",
    allow_preview=True,    # tap to open full-screen preview
    elem_id="swipe-gallery",
)
```

```css
#swipe-gallery .gallery-item {
  scroll-snap-type: x mandatory;
  overflow-x: scroll;
}
```

---

## 8. Touch input — scroll and drag

### Preventing scroll hijacking

If a component intercepts vertical scroll (e.g., a custom Svelte slider), always set
`touch-action` to allow the native scroll:

```css
/* Allow vertical scroll on horizontally-draggable elements */
.h-draggable { touch-action: pan-y; }

/* Allow horizontal scroll on vertically-draggable elements */
.v-draggable { touch-action: pan-x; }
```

### `gr.Slider` on touch

Gradio's built-in `gr.Slider` works on touch, but the drag handle can be hard to hit on
small screens. Use `elem_classes` and CSS to enlarge it:

```css
.gr-slider .gr-range-slider-thumb {
  width: 24px !important;
  height: 24px !important;
  margin-top: -10px !important;
}
```

### Scrollable output areas

For long text outputs, constrain height and enable scroll rather than expanding the page:

```python
output_text = gr.Textbox(
    label="Output",
    lines=10,
    max_lines=30,
    autoscroll=True,    # Gradio 6.9 — scrolls to new content automatically
    elem_id="output-text",
)
```

---

## 9. Keyboard and mouse enhancements

### Submit on Enter

```python
prompt_box = gr.Textbox(
    submit_btn=True,   # shows Enter button in the input field
    lines=1,           # single-line: Enter submits; multi-line: Shift+Enter submits
)
```

For multi-line inputs where you want Enter to submit:

```python
gr.on(
    triggers=[prompt_box.submit, run_btn.click],
    fn=generate,
    inputs=[prompt_box],
    outputs=[output_img],
)
```

### Keyboard shortcuts

```python
gr.HTML("""
<script>
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    document.getElementById('run-btn')?.click();
  }
});
</script>
""")
```

### Mouse hover tooltips

```python
steps_slider = gr.Slider(
    1, 50, value=20,
    label="Inference steps",
    info="More steps = better quality but slower. 20–30 is usually the sweet spot.",
)
```

The `info=` text appears as a hover tooltip on desktop and as helper text on mobile —
a single field that serves both input modes.

---

## 10. Accessibility considerations

- Use `label=` on every input component — screen readers and voice control rely on it.
- `gr.Image` alt text: Gradio sets `alt=""` by default; for static images use
  `gr.HTML('<img src="…" alt="descriptive text">')`.
- Colour contrast: Gradio's built-in themes meet WCAG AA. If you use custom colours,
  check with a contrast checker (aim for 4.5:1 for body text).
- Focus indicators: Do not suppress `:focus` outlines in your custom CSS unless you
  provide an equivalent alternative.
- `aria-label` for icon-only buttons:
  ```python
  gr.Button("🔁", elem_classes=["icon-btn"], value="Refresh", label="Refresh history")
  ```

---

## 11. Testing on real devices

You cannot fully validate touch UX in a browser DevTools emulator. Test on:

1. **Chrome DevTools → Device Mode** — reasonable first pass for layout.
2. **Safari on iOS** — different touch event model; font-size zoom prevention is iOS-specific.
3. **Android Chrome** — most common mobile browser globally.
4. **Tablet (e.g., iPad)** — the 600–899 px mid-range breakpoint.

For HuggingFace Spaces, share the Space URL with a phone and tap through the critical
paths before publishing widely.

### Common mobile issues to check

| Issue | Cause | Fix |
|---|---|---|
| Input zooms on focus | `font-size < 16px` on iOS | Set `font-size: 16px` in CSS |
| Buttons too small to tap | `size="sm"` or custom CSS | Use `size="lg"` or `min-height: 48px` |
| Horizontal scrollbar appears | Fixed-width element wider than viewport | Add `overflow-x: hidden` to `body`, or fix width |
| Swipe navigates the browser back/forward | App catches all horizontal swipes | Only handle swipes that start within the swipeable element |
| Double-tap zooms unexpectedly | Default browser behaviour | Add `<meta name="viewport" content="…, user-scalable=no">` (carefully — harms accessibility) |
