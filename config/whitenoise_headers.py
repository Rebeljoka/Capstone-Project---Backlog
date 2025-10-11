"""
Custom WhiteNoise headers hook to control cache lifetimes for selected assets.

Applies a 6-month cache (15638400 seconds) to image and font assets so browsers
keep them longer. Other assets keep WhiteNoise defaults (immutable for hashed
files; WHITENOISE_MAX_AGE for others).
"""
from __future__ import annotations

from typing import Dict


SIX_MONTHS = 15638400


IMAGE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".ico",
    ".avif",
}

FONT_EXTS = {
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
}

OTHER_EXTS = {
    ".js",
    ".css",
    ".woff2"
}


def set_custom_cache_headers(headers: Dict[str, str], path: str, url: str) -> None:
    """
    WhiteNoise hook: mutate headers per-file.

    Args:
        headers: Response headers dict for the static asset
        path: Filesystem path to the asset
        url: URL path used to access the asset (leading slash)
    """
    # If WhiteNoise already marked as immutable (hashed file), leave it as-is
    cache_control = headers.get("Cache-Control", "")
    if "immutable" in cache_control:
        return

    lowered = path.lower()
    # Apply 6-month cache to images and fonts
    if any(lowered.endswith(ext) for ext in (IMAGE_EXTS | FONT_EXTS | OTHER_EXTS)):
        headers["Cache-Control"] = f"public, max-age={SIX_MONTHS}"
