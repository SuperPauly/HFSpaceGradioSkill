#!/usr/bin/env python3
"""
scaffold_custom_component.py
────────────────────────────
Scaffold a new Gradio 6.9.0 custom component with BunJS + optional Shadcn-Svelte.

Usage:
  python scaffold_custom_component.py --name my-rating --template slider --shadcn
  python scaffold_custom_component.py --name my-chart --template textbox
  python scaffold_custom_component.py --help

Requirements:
  - Python >= 3.10
  - gradio >= 6.9.0  (pip install "gradio[components]>=6.9.0")
  - bun >= 1.1       (curl -fsSL https://bun.sh/install | bash)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


# ── Available built-in Gradio component templates ──────────────────────────────
VALID_TEMPLATES = [
    "slider",
    "textbox",
    "image",
    "audio",
    "video",
    "file",
    "checkbox",
    "radio",
    "dropdown",
    "number",
    "annotatedimage",
    "chatbot",
    "code",
    "gallery",
]

# ── Shadcn-Svelte packages to install when --shadcn is passed ──────────────────
SHADCN_PACKAGES = [
    "shadcn-svelte",
    "bits-ui",
    "svelte-sonner",
]

# ── Tailwind + PostCSS devDependencies needed for Shadcn ──────────────────────
SHADCN_DEV_PACKAGES = [
    "tailwindcss",
    "autoprefixer",
    "postcss",
]

# ── Shadcn starter snippet injected into Index.svelte ─────────────────────────
SHADCN_SVELTE_SNIPPET = """\
<!-- Shadcn-Svelte starter — replace this placeholder with your component -->
<script lang="ts">
  import {{ Button }} from "shadcn-svelte";
  import type {{ Gradio }} from "@gradio/utils";

  export let gradio: Gradio<{{ change: never }}>;
  export let value: string = "";
  export let label: string = "";
</script>

<div class="w-full max-w-md mx-auto p-4">
  <p class="text-sm font-medium mb-2">{{label}}</p>
  <Button on:click={{() => gradio.dispatch("change")}}>
    Click me
  </Button>
</div>
"""

TAILWIND_CONFIG = """\
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./src/**/*.{svelte,ts,js,html}",
    "./node_modules/shadcn-svelte/**/*.svelte",
  ],
  theme: { extend: {} },
  plugins: [],
};
"""

POSTCSS_CONFIG = """\
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""


def check_dependency(name: str, check_cmd: list[str]) -> None:
    """Raise SystemExit if a required external tool is missing."""
    try:
        subprocess.run(check_cmd, capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"❌  '{name}' not found. Please install it first.", file=sys.stderr)
        if name == "gradio":
            print("    pip install 'gradio[components]>=6.9.0'", file=sys.stderr)
        elif name == "bun":
            print("    curl -fsSL https://bun.sh/install | bash", file=sys.stderr)
        sys.exit(1)


def run(cmd: list[str], cwd: Path | None = None, label: str = "") -> None:
    """Run a shell command, streaming output, and exit on failure."""
    display = label or " ".join(cmd)
    print(f"  ▶  {display}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"❌  Command failed: {display}", file=sys.stderr)
        sys.exit(result.returncode)


def scaffold(name: str, template: str, output_dir: Path, shadcn: bool, dry_run: bool) -> None:
    """Run `gradio cc create` and optionally install Shadcn."""

    component_dir = output_dir / name.replace("-", "_")

    if component_dir.exists():
        print(f"❌  Directory already exists: {component_dir}", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        print(f"[dry-run] Would run: gradio cc create {name} --template {template}")
        print(f"[dry-run] Output: {component_dir}")
        if shadcn:
            print(f"[dry-run] Would install Shadcn packages: {', '.join(SHADCN_PACKAGES)}")
        return

    # ── Step 1: scaffold via Gradio CLI ────────────────────────────────────────
    print(f"\n🏗  Scaffolding '{name}' from template '{template}'…")
    run(
        ["gradio", "cc", "create", name, "--template", template],
        cwd=output_dir,
        label=f"gradio cc create {name} --template {template}",
    )

    frontend_dir = component_dir / "frontend"

    # ── Step 2: replace npm/pnpm lock file with bun ────────────────────────────
    for lock in ["package-lock.json", "pnpm-lock.yaml", "yarn.lock"]:
        lock_file = frontend_dir / lock
        if lock_file.exists():
            lock_file.unlink()
            print(f"  🗑   Removed {lock}")

    print("\n📦  Installing frontend dependencies with Bun…")
    run(["bun", "install"], cwd=frontend_dir, label="bun install")

    # ── Step 3: optional Shadcn setup ─────────────────────────────────────────
    if shadcn:
        print("\n🎨  Installing Shadcn-Svelte and Tailwind…")
        run(
            ["bun", "add"] + SHADCN_PACKAGES,
            cwd=frontend_dir,
            label="bun add shadcn-svelte bits-ui svelte-sonner",
        )
        run(
            ["bun", "add", "-D"] + SHADCN_DEV_PACKAGES,
            cwd=frontend_dir,
            label="bun add -D tailwindcss autoprefixer postcss",
        )

        # Write Tailwind and PostCSS config
        (frontend_dir / "tailwind.config.js").write_text(TAILWIND_CONFIG)
        (frontend_dir / "postcss.config.js").write_text(POSTCSS_CONFIG)
        print("  ✅  Wrote tailwind.config.js and postcss.config.js")

        # Inject Shadcn starter into Index.svelte
        index_svelte = frontend_dir / "src" / "Index.svelte"
        if index_svelte.exists():
            original = index_svelte.read_text()
            # Prepend the Shadcn snippet as a comment-block so users can see both
            index_svelte.write_text(
                f"<!-- AUTO-GENERATED: Shadcn starter. Remove this block and write your own. -->\n"
                f"{SHADCN_SVELTE_SNIPPET}\n"
                f"<!-- ORIGINAL SCAFFOLD OUTPUT:\n{original}\n-->"
            )
            print(f"  ✅  Injected Shadcn starter into {index_svelte}")

        # Update package.json to use Tailwind CSS processing
        pkg_json_path = frontend_dir / "package.json"
        if pkg_json_path.exists():
            pkg = json.loads(pkg_json_path.read_text())
            pkg.setdefault("scripts", {})
            pkg["scripts"]["build:css"] = "tailwindcss -i ./src/app.css -o ./src/app.out.css"
            pkg_json_path.write_text(json.dumps(pkg, indent=2) + "\n")
            print("  ✅  Added build:css script to package.json")

    # ── Step 4: summary ────────────────────────────────────────────────────────
    print(f"""
✅  Scaffolding complete!

Component directory : {component_dir}
Frontend workspace  : {frontend_dir}

Next steps:
  1. Edit the backend class in  {component_dir}/backend/{name.replace('-', '_')}/{name.replace('-', '_')}.py
  2. Edit the Svelte component  {frontend_dir}/src/Index.svelte
  3. Run the dev server:
       cd {component_dir} && gradio cc dev
  4. When ready to build:
       cd {component_dir} && gradio cc build
  5. Publish to HuggingFace Hub:
       cd {component_dir} && gradio cc publish
""")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a Gradio 6.9.0 custom component with BunJS + optional Shadcn.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scaffold_custom_component.py --name my-rating --template slider --shadcn
  python scaffold_custom_component.py --name my-chart --template textbox --output ./components
  python scaffold_custom_component.py --name my-combo --template dropdown --shadcn --dry-run

Available templates:
  """ + ", ".join(VALID_TEMPLATES),
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Component name (lowercase, hyphens allowed, e.g. 'my-rating')",
    )
    parser.add_argument(
        "--template",
        default="slider",
        choices=VALID_TEMPLATES,
        help="Built-in Gradio component template to start from (default: slider)",
    )
    parser.add_argument(
        "--output",
        default=".",
        help="Directory in which to create the component folder (default: current dir)",
    )
    parser.add_argument(
        "--shadcn",
        action="store_true",
        help="Install Shadcn-Svelte, Bits UI, Tailwind and inject a starter snippet",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without executing any commands",
    )

    args = parser.parse_args()

    # Validate name
    import re
    if not re.fullmatch(r"[a-z][a-z0-9-]*[a-z0-9]", args.name):
        print(
            "❌  --name must be lowercase letters, digits, and hyphens, "
            "starting and ending with a letter/digit.",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = Path(args.output).expanduser().resolve()
    if not output_dir.exists():
        print(f"❌  Output directory does not exist: {output_dir}", file=sys.stderr)
        sys.exit(1)

    if not args.dry_run:
        check_dependency("gradio", ["gradio", "--version"])
        check_dependency("bun", ["bun", "--version"])

    scaffold(
        name=args.name,
        template=args.template,
        output_dir=output_dir,
        shadcn=args.shadcn,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
