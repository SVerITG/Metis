"""AI image generation and listing tools."""

import datetime
import json
import os
import re

from mcp.types import TextContent

from metis_mcp.config import paths
from metis_mcp.app_instance import app


def _images_dir():
    d = paths.root / "07_outputs" / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_slug(prompt: str) -> str:
    slug = prompt[:40].lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def _make_filename(prompt: str, output_filename: str) -> str:
    if output_filename:
        return output_filename
    date_str = datetime.date.today().isoformat()
    slug = _make_slug(prompt)
    return f"{date_str}_{slug}"


def _write_sidecar(image_path, prompt: str, backend: str, model: str):
    sidecar = image_path.with_suffix(".json")
    sidecar.write_text(
        json.dumps(
            {
                "prompt": prompt,
                "backend": backend,
                "model": model,
                "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


@app.tool()
async def generate_image(
    prompt: str,
    backend: str = "gemini",
    model: str = "flash",
    width: int = 1024,
    height: int = 1024,
    output_filename: str = "",
) -> list[TextContent]:
    """Generate an image using AI and save it to the PKM.

    Saves to {pkm_root}/07_outputs/images/YYYY-MM-DD_[slug].png

    Args:
        prompt: Description of the image to generate.
        backend: "gemini" (default) or "huggingface"
        model: "flash" (gemini-3.1-flash-preview-image-generation),
               "imagen" (imagen-4.0-generate-001),
               "flux" (FLUX.1-schnell via HuggingFace)
        width: Image width in pixels (default 1024).
        height: Image height in pixels (default 1024).
        output_filename: Optional custom filename (without extension).
    """
    images_dir = _images_dir()
    stem = _make_filename(prompt, output_filename)
    output_path = images_dir / f"{stem}.png"

    image_bytes: bytes | None = None

    if backend == "gemini":
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            return [
                TextContent(
                    type="text",
                    text="google-genai not installed. Run: pip install google-genai pillow",
                )
            ]

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return [
                TextContent(
                    type="text",
                    text="GEMINI_API_KEY not set. Get a free key at https://aistudio.google.com",
                )
            ]

        client = genai.Client(api_key=api_key)

        try:
            if model == "imagen":
                response = client.models.generate_images(
                    model="imagen-4.0-generate-001",
                    prompt=prompt,
                    config=types.GenerateImagesConfig(number_of_images=1),
                )
                image_bytes = response.generated_images[0].image.image_bytes
            else:
                # Default: flash
                response = client.models.generate_content(
                    model="gemini-3.1-flash-preview-image-generation",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE", "TEXT"]
                    ),
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_bytes = part.inline_data.data
                        break
        except Exception as e:
            return [TextContent(type="text", text=f"Gemini API error: {e}")]

    elif backend == "huggingface":
        import requests

        hf_token = os.environ.get("HF_API_TOKEN")
        if not hf_token:
            return [
                TextContent(
                    type="text",
                    text="HF_API_TOKEN not set. Get a free token at https://huggingface.co/settings/tokens",
                )
            ]

        api_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
        headers = {"Authorization": f"Bearer {hf_token}"}
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": prompt},
                timeout=60,
            )
            if response.status_code == 200:
                image_bytes = response.content
            else:
                return [
                    TextContent(
                        type="text",
                        text=f"HuggingFace API error {response.status_code}: {response.text}",
                    )
                ]
        except Exception as e:
            return [TextContent(type="text", text=f"HuggingFace request error: {e}")]

    else:
        return [
            TextContent(
                type="text",
                text=f"Unknown backend '{backend}'. Use 'gemini' or 'huggingface'.",
            )
        ]

    if not image_bytes:
        return [
            TextContent(
                type="text",
                text="No image data returned from the API. The model may not have produced an image for this prompt.",
            )
        ]

    output_path.write_bytes(image_bytes)
    _write_sidecar(output_path, prompt, backend, model)

    return [
        TextContent(
            type="text",
            text=f"Image saved to: {output_path}\nPrompt: {prompt}\nBackend: {backend}, Model: {model}",
        )
    ]


@app.tool()
async def list_generated_images(limit: int = 20) -> list[TextContent]:
    """List recently generated images in the PKM.

    Reads from {pkm_root}/07_outputs/images/ directory.
    Returns filename, date, and prompt (from JSON sidecar if present).

    Args:
        limit: Maximum number of images to return (default 20, newest first).
    """
    images_dir = _images_dir()

    try:
        png_files = sorted(
            images_dir.glob("*.png"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except Exception as e:
        return [TextContent(type="text", text=f"Error scanning images directory: {e}")]

    if not png_files:
        return [
            TextContent(
                type="text",
                text=f"No images found in {images_dir}",
            )
        ]

    png_files = png_files[:limit]
    lines = [f"Generated images ({len(png_files)} shown, newest first):\n"]

    for img_path in png_files:
        mtime = datetime.datetime.fromtimestamp(
            img_path.stat().st_mtime, tz=datetime.timezone.utc
        )
        date_str = mtime.strftime("%Y-%m-%d %H:%M UTC")

        sidecar = img_path.with_suffix(".json")
        prompt_info = ""
        backend_info = ""
        if sidecar.exists():
            try:
                meta = json.loads(sidecar.read_text(encoding="utf-8"))
                prompt_info = f"\n    Prompt: {meta.get('prompt', '')}"
                backend_info = (
                    f"\n    Backend: {meta.get('backend', '')}, "
                    f"Model: {meta.get('model', '')}"
                )
            except Exception:
                pass

        lines.append(f"- {img_path.name}  [{date_str}]{prompt_info}{backend_info}")

    return [TextContent(type="text", text="\n".join(lines))]
