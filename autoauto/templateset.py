"""Multi-resolution template sets.

A UI element captured on a 1080p phone won't template-match on a 720p one. A
`TemplateSet` holds several images of the *same* target (captured at different
resolutions/DPI, or auto-scaled from one) and matches against all of them,
returning the best hit. This is more reliable than single-scale matching when
scripts run across a fleet of differently-sized devices.
"""
from __future__ import annotations

import cv2
import numpy as np

from . import vision
from .geometry import Rect
from .vision import MatchResult


def scale_template(template: np.ndarray, ref_wh: tuple[int, int],
                   dev_wh: tuple[int, int]) -> np.ndarray:
    """Resize a template captured at `ref_wh` to the ratio of `dev_wh`."""
    rw, rh = ref_wh
    dw, dh = dev_wh
    if rw <= 0 or rh <= 0:
        raise ValueError("reference size must be positive")
    fx, fy = dw / rw, dh / rh
    if abs(fx - 1.0) < 1e-6 and abs(fy - 1.0) < 1e-6:
        return template
    interp = cv2.INTER_AREA if (fx < 1 or fy < 1) else cv2.INTER_LINEAR
    return cv2.resize(template, None, fx=fx, fy=fy, interpolation=interp)


class TemplateSet:
    """A named collection of equivalent templates at different resolutions."""

    def __init__(self, name: str, templates: list[np.ndarray]) -> None:
        if not templates:
            raise ValueError("TemplateSet needs at least one template")
        self.name = name
        self.templates = templates

    @classmethod
    def from_paths(cls, name: str, paths: list[str]) -> "TemplateSet":
        imgs = []
        for p in paths:
            img = cv2.imread(p, cv2.IMREAD_COLOR)
            if img is None:
                raise FileNotFoundError(f"template not found: {p}")
            imgs.append(img)
        return cls(name, imgs)

    @classmethod
    def scaled_variants(cls, name: str, template: np.ndarray,
                        ref_wh: tuple[int, int],
                        dev_sizes: list[tuple[int, int]]) -> "TemplateSet":
        """Build a set by scaling one reference template to several device sizes."""
        variants = [scale_template(template, ref_wh, d) for d in dev_sizes]
        return cls(name, variants)

    def find_indexed(self, image: np.ndarray, threshold: float = 0.85,
                     region: Rect | None = None) -> tuple[int, MatchResult]:
        """Return (best_template_index, MatchResult) across all templates."""
        best_i = -1
        best = MatchResult(False, 0.0)
        for i, tpl in enumerate(self.templates):
            if image.shape[0] < tpl.shape[0] or image.shape[1] < tpl.shape[1]:
                continue
            r = vision.find_template(image, tpl, threshold=0.0, region=region)
            if r.score > best.score:
                best, best_i = r, i
        best.found = best.score >= threshold
        if not best.found:
            best.rect = None
        return best_i, best

    def find(self, image: np.ndarray, threshold: float = 0.85,
             region: Rect | None = None) -> MatchResult:
        return self.find_indexed(image, threshold, region)[1]
