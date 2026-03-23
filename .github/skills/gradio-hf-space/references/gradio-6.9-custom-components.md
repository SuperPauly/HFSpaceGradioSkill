# Gradio 6.9.0 Custom Components — BunJS + Shadcn Reference

This document covers building, structuring, and publishing custom Gradio 6.9.0 components
using the official `gradio cc` CLI, the **Bun** JavaScript runtime, and **Shadcn-Svelte**
for UI primitives.

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Component architecture](#2-component-architecture)
3. [Scaffolding and project structure](#3-scaffolding-and-project-structure)
4. [Backend Python class](#4-backend-python-class)
5. [Frontend Svelte + Bun workspace](#5-frontend-svelte--bun-workspace)
6. [Adding Shadcn-Svelte and third-party components](#6-adding-shadcn-svelte-and-third-party-components)
7. [Async and streaming inside custom components](#7-async-and-streaming-inside-custom-components)
8. [Responsive layout inside a custom component](#8-responsive-layout-inside-a-custom-component)
9. [Touch UX inside Svelte components](#9-touch-ux-inside-svelte-components)
10. [Build and publish](#10-build-and-publish)
11. [Common pitfalls](#11-common-pitfalls)

---

## 1. Prerequisites

| Requirement | Version |
|---|---|
| Python | ≥ 3.10 |
| Gradio | 6.9.0 |
| Bun | ≥ 1.1 (`curl -fsSL https://bun.sh/install \| bash`) |
| Node.js | ≥ 18 (used by some Bun plugins) |

Install Gradio with the component extras:

```bash
pip install "gradio[components]>=6.9.0"
```

---

## 2. Component architecture

A Gradio custom component has two parts that communicate over a defined value contract:

```
┌─────────────────────────────────────────────────────────────┐
│  Python side (backend)                                      │
│  ─────────────────────────────────────────────────────────  │
│  Component class (inherits gr.Component)                    │
│   • preprocess(payload) → Python value sent to event fn     │
│   • postprocess(value) → payload serialised to JSON/binary  │
│   • api_info() → OpenAPI schema for the component value     │
│   • example_payload() → sample value for the Gradio docs UI │
└───────────────────────┬─────────────────────────────────────┘
                        │  JSON / binary blob
┌───────────────────────▼─────────────────────────────────────┐
│  Svelte/TypeScript side (frontend)                          │
│  ─────────────────────────────────────────────────────────  │
│  Index.svelte — receives `value` prop, emits events via     │
│  the `gradio` context object                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Scaffolding and project structure

```bash
gradio cc create my-rating --template slider
```

Produces:

```
my_rating/
├── pyproject.toml
├── backend/
│   └── my_rating/
│       ├── __init__.py
│       └── my_rating.py     ← Python component class
├── frontend/
│   ├── package.json         ← "type": "module", bun workspace
│   ├── bun.lockb
│   ├── svelte.config.js
│   ├── vite.config.ts
│   └── src/
│       ├── Index.svelte      ← primary component export
│       ├── app.css           ← global styles (Tailwind base)
│       └── lib/              ← sub-components
│           └── shared/
│               └── utils.ts
└── demo/
    └── app.py                ← development demo
```

Available templates: `slider`, `textbox`, `image`, `audio`, `video`, `file`,
`checkbox`, `radio`, `dropdown`, `number`, `annotatedimage`, `chatbot`, `code`, `gallery`.

Pick the template whose value type most closely matches yours — it minimises the amount of
boilerplate you rewrite.

---

## 4. Backend Python class

```python
# backend/my_rating/my_rating.py
from __future__ import annotations
from gradio.components.base import Component
from gradio import processing_utils
from gradio.events import Events


class MyRating(Component):
    """A star-rating component."""

    EVENTS = [Events.change, Events.select]

    def __init__(
        self,
        value: int = 0,
        *,
        label: str | None = None,
        max_stars: int = 5,
        elem_id: str | None = None,
        elem_classes: list[str] | str | None = None,
        visible: bool = True,
        interactive: bool | None = None,
    ):
        self.max_stars = max_stars
        super().__init__(
            value=value,
            label=label,
            elem_id=elem_id,
            elem_classes=elem_classes,
            visible=visible,
            interactive=interactive,
        )

    def preprocess(self, payload: int | None) -> int | None:
        """Called before value is passed to an event function."""
        return payload

    def postprocess(self, value: int | None) -> int | None:
        """Called after an event function returns."""
        return value

    def api_info(self) -> dict:
        return {"type": "integer"}

    def example_payload(self) -> int:
        return 3

    def example_value(self) -> int:
        return 3
```

---

## 5. Frontend Svelte + Bun workspace

### `package.json`

```json
{
  "name": "my-rating-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "devDependencies": {
    "@sveltejs/vite-plugin-svelte": "^3.0.0",
    "svelte": "^5.0.0",
    "svelte-check": "^3.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

Install with Bun (not npm/pnpm):

```bash
cd frontend && bun install
```

### `src/Index.svelte` — minimal component

```svelte
<script lang="ts">
  import type { Gradio } from "@gradio/utils";
  import { Block } from "@gradio/atoms";

  // Props injected by Gradio
  export let gradio: Gradio<{ change: never; select: { index: number } }>;
  export let value: number = 0;
  export let label: string = "";
  export let max_stars: number = 5;
  export let interactive: boolean = true;

  function select(star: number) {
    if (!interactive) return;
    value = star;
    gradio.dispatch("change");
    gradio.dispatch("select", { index: star });
  }
</script>

<Block label={label}>
  <div class="flex gap-1">
    {#each Array(max_stars) as _, i}
      <button
        class="text-2xl transition-colors focus:outline-none
               {i < value ? 'text-yellow-400' : 'text-gray-300'}"
        on:click={() => select(i + 1)}
        aria-label={`Rate ${i + 1} out of ${max_stars}`}
      >★</button>
    {/each}
  </div>
</Block>
```

---

## 6. Adding Shadcn-Svelte and third-party components

### Install core Shadcn-Svelte

```bash
cd frontend
bun add shadcn-svelte @shadcn-svelte/ui bits-ui
```

Shadcn-Svelte uses the **Bits UI** primitives library (headless, accessible) as its
foundation.

### Initialize Tailwind (if not present)

```bash
bun add -D tailwindcss autoprefixer postcss
bunx tailwindcss init -p
```

Add to `tailwind.config.js`:

```js
export default {
  content: ["./src/**/*.{svelte,ts,js}"],
  theme: { extend: {} },
  plugins: [],
};
```

### Component import pattern

```svelte
<script lang="ts">
  import { Slider } from "shadcn-svelte";
  import { Button } from "shadcn-svelte";
  import { Badge } from "shadcn-svelte";
</script>
```

### Recommended third-party Shadcn ecosystem packages

| Package | Provides | Install |
|---|---|---|
| `shadcn-svelte` | Core components (Button, Dialog, Slider, etc.) | `bun add shadcn-svelte` |
| `bits-ui` | Headless primitives (Accordion, Combobox, etc.) | `bun add bits-ui` |
| `@huntabyte/primitives` | Drawer, Context Menu, Tooltip | `bun add @huntabyte/primitives` |
| `svelte-sonner` | Toast notifications | `bun add svelte-sonner` |
| `layerchart` | SVG charts (area, bar, line) | `bun add layerchart` |
| `svelte-motion` | Animation primitives (Framer Motion port) | `bun add svelte-motion` |

### Example: Shadcn Combobox inside a Gradio component

```svelte
<script lang="ts">
  import { Combobox } from "bits-ui";
  import type { Gradio } from "@gradio/utils";

  export let gradio: Gradio<{ change: never }>;
  export let value: string = "";
  export let choices: string[] = [];

  let open = false;

  function pick(item: string) {
    value = item;
    open = false;
    gradio.dispatch("change");
  }
</script>

<Combobox.Root bind:open onSelectedChange={(v) => v && pick(v.value)}>
  <Combobox.Input placeholder="Select…" />
  <Combobox.Content>
    {#each choices as choice}
      <Combobox.Item value={choice}>{choice}</Combobox.Item>
    {/each}
  </Combobox.Content>
</Combobox.Root>
```

---

## 7. Async and streaming inside custom components

Custom component frontends are synchronous Svelte, but you can fake streaming by
reading a `gr.State` variable that the backend updates:

Backend:

```python
@spaces.GPU
def generate_stream(prompt: str):
    model = get_model()
    tokens = ""
    for chunk in model.stream(prompt):
        tokens += chunk
        yield tokens    # Gradio streams intermediate values to the frontend
```

Frontend: The streaming value arrives via the regular `value` prop — Svelte's reactivity
handles the incremental updates automatically.

---

## 8. Responsive layout inside a custom component

Use Tailwind's responsive prefixes to handle 9:16 vs 16:9 directly inside the Svelte
component without needing the parent app's CSS:

```svelte
<div class="
  flex flex-col         /* stack on portrait */
  sm:flex-row           /* side-by-side on ≥640px */
  gap-4 p-4
  w-full max-w-2xl
">
  <div class="w-full sm:w-1/3">
    <!-- Input area -->
  </div>
  <div class="w-full sm:w-2/3">
    <!-- Output area -->
  </div>
</div>
```

Tailwind breakpoints (default):

| Prefix | Min-width | Good for |
|---|---|---|
| `sm:` | 640 px | Landscape phone / large portrait tablet |
| `md:` | 768 px | Tablet |
| `lg:` | 1024 px | Desktop / laptop |
| `xl:` | 1280 px | Wide desktop |

---

## 9. Touch UX inside Svelte components

```svelte
<script lang="ts">
  let startX = 0;

  function onTouchStart(e: TouchEvent) {
    startX = e.touches[0].clientX;
  }

  function onTouchEnd(e: TouchEvent) {
    const deltaX = e.changedTouches[0].clientX - startX;
    if (deltaX > 50) handleSwipeRight();
    if (deltaX < -50) handleSwipeLeft();
  }
</script>

<div
  on:touchstart={onTouchStart}
  on:touchend={onTouchEnd}
  class="touch-pan-y"     <!-- Tailwind: allow vertical scroll, intercept horizontal -->
>
  <!-- swipeable content -->
</div>
```

Always set `touch-action: pan-y` (or the Tailwind `touch-pan-y` class) on swipeable
containers so vertical scrolling still works normally and the browser doesn't interfere.

---

## 10. Build and publish

```bash
# From component root (my_rating/)
gradio cc build       # compiles frontend, produces dist/

# Test locally in another project
pip install /path/to/my_rating

# Publish to HuggingFace Hub (requires `huggingface-cli login`)
gradio cc publish
```

After publishing, users install your component with:

```bash
pip install my-rating
```

And import it:

```python
from my_rating import MyRating
```

---

## 11. Common pitfalls

| Pitfall | Fix |
|---|---|
| Using `npm install` instead of `bun install` | Always run `bun install` inside `frontend/` — mixing lock files breaks the build |
| Importing Shadcn React components | Gradio uses Svelte; use `shadcn-svelte`, not `@shadcn-ui/react` |
| `gradio.dispatch` called before component mounts | Wrap in `onMount` or guard with `if (mounted)` |
| Tailwind classes not applied | Ensure `content` in `tailwind.config.js` covers all `.svelte` files in `src/` |
| `preprocess` receives `null` on first load | Always handle `null`/`undefined` in `preprocess` — the component may render before a value is set |
| HMR not working in `gradio cc dev` | Check that `vite.config.ts` has `server: { hmr: true }` |
