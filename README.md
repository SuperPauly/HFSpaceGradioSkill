# 🤗 HFSpaceGradioSkill

> A GitHub Copilot skill for building production-quality **Gradio 6.9.0** apps on **HuggingFace Spaces**.

The canonical skill specification lives at:
📄 `.github/skills/gradio-hf-space/SKILL.md`

When this repository is opened in Copilot, all Gradio/HuggingFace Space guidance should follow that file.

---

## ⚠️ GitHub Web Only — Not for CLI

> **This skill is designed exclusively for use with GitHub Copilot on the GitHub website.**
>
> It is **not** compatible with the GitHub Copilot CLI, VS Code Copilot Chat, or any other local/desktop Copilot interface.
>
> You must use one of the following on **github.com**:
> - **Copilot Chat (Web)** — via the Copilot icon on your repository page
> - **Copilot Coding Agent (Web)** — via Issues or the Copilot agent interface

---

## 🧠 What This Skill Covers

The `gradio-hf-space` skill (`SKILL.md`) is an expert guide covering:

| Topic | Description |
|---|---|
| **Quick-start pattern** | Minimal `app.py` skeleton for Gradio 6.9.0 Spaces |
| **Responsive layouts** | 9:16 (mobile) and 16:9 (desktop) unified CSS grid layouts |
| **Touchscreen UX** | Tap, swipe, scroll — WCAG-compliant touch-friendly ML UIs |
| **Custom components** | Building Svelte 5 components with BunJS + Shadcn-Svelte |
| **Async model loading** | Non-blocking lazy model initialisation patterns |
| **Zero GPU decorator** | `@spaces.GPU` usage, multi-model Spaces, GPU memory management |
| **HF Spaces limits** | Hard limits, model count guidance, memory optimisation tips |
| **UI performance** | Streaming, debouncing, optimistic UI, `gr.on`, caching |

---

## 🚀 Quickstart

### Option A — Use This Template (Recommended)

1. Click **Use this template** on GitHub.
2. Create your new repository from this template.
3. Open your new repo and start **Copilot Chat** or **Copilot Coding Agent** (Web).
4. Ask Copilot anything about Gradio, HuggingFace Spaces, Zero GPU, or responsive ML UIs.
5. Copilot will automatically apply the skill from `.github/skills/gradio-hf-space/SKILL.md`.

### Option B — Reference Directly

Point Copilot at the skill file manually:

> "Use `.github/skills/gradio-hf-space/SKILL.md` to help me build a Gradio Space."

---

## 🔌 Recommended MCP Servers

Enhance Copilot's context by connecting MCP servers with live Gradio and HuggingFace documentation:

```json
{
  "mcpServers": {
    "gradio": {
      "type": "http",
      "tools": ["*"],
      "url": "https://gradio-docs-mcp.hf.space/gradio_api/mcp/"
    },
    "hf-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@huggingface/hf-mcp-server"],
      "tools": ["*"],
      "env": {
        "HF_TOKEN": "$HF_READ"
      }
    },
    "deepwiki": {
      "type": "http",
      "tools": ["*"],
      "url": "https://mcp.deepwiki.com/mcp"
    }
  }
}
```

### How to add MCP servers

1. Go to your repository on **github.com**.
2. Click **Settings** → **Copilot** → **MCP Servers**.
3. Paste the JSON configuration above.

### 🔑 HuggingFace API Key (required for `hf-mcp-server`)

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) and create a **Read** token.
2. In your GitHub repo, go to **Settings** → **Secrets and variables** → **Actions**.
3. Click **New repository secret**, name it `HF_READ`, and paste your token.

---

## 📁 Skill Structure

```
.github/skills/gradio-hf-space/
├── SKILL.md                  ← Main skill specification (required)
├── references/               ← Deep-dive reference docs
│   ├── gradio-6.9-custom-components.md
│   ├── hf-spaces-zerogpu.md
│   └── responsive-layout.md
├── evals/                    ← Evaluation cases
└── scripts/                  ← Helper scripts
    ├── scaffold_custom_component.py
    └── demo_app.py
```

---

## ✨ Skill Trigger Keywords

Copilot will automatically apply this skill when you mention any of:

`gradio` · `hf space` · `huggingface space` · `zero gpu` · `shadcn gradio` · `responsive ML app` · `custom gradio component` · `BunJS gradio`

---

## 🔄 Skill Workflows

| Workflow | Description |
|---|---|
| **Build a new Space** | Scaffold a complete Gradio app with responsive layout and async model loading |
| **Add a custom component** | Create a BunJS + Shadcn Svelte component and wire it into a Space |
| **Optimise for Zero GPU** | Apply `@spaces.GPU`, lazy loading, and memory management patterns |
| **Make a Space mobile-friendly** | Add CSS breakpoints and touch-optimised UX |

---

## 🧹 Post-Setup Cleanup

> ⚠️ **Important:** Only run this after your generated skill files are committed and verified.

Once your skill is ready, remove the original template scaffolding:

1. Go to the **Actions** tab in your repository.
2. Run the **Delete template files only (manual)** workflow.
3. Confirm the workflow completes successfully.

---

*Built with the [SkillCreatorSkill](https://github.com/SuperPauly/SkillCreatorSkill) template.*