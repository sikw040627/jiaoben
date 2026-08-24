"""Computer-vision primitives: find-image, find-color, multi-point color.

These mirror the bread-and-butter 自动精灵 operations:
  * 找图  -> find_template / find_all_templates (template matching, +/- scale)
  * 找色  -> find_color / count_color
  * 多点比色 -> match_multi_color (anchor pixel + relative offset checks)
  * 取色  -> get_pixel

All functions operate on BGR uint8 numpy images (OpenCV convention). Colors are
passed by the caller as **RGB** tuples because that is what humans read off a
colour picker; conversion to BGR happens internally.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .geometry import Point, Rect


@dataclass
class MatchResult:
    found: bool
    score: float
    rect: Rect | None = None

    @property
    def center(self) -> Point | None:
        return self.rect.center if self.rect else None

    def __bool__(self) -> bool:
        return self.found


def _region_offset(region: Rect | None) -> tuple[int, int]:
    return (region.left, region.top) if region else (0, 0)


def _crop(image: np.ndarray, region: Rect | None) -> np.ndarray:
    if region is None:
        return image
    rows, cols = region.as_slice()
    return image[rows, cols]


# -- template matching (找图) -------------------------------------------------
def find_template(image: np.ndarray, template: np.ndarray,
                  threshold: float = 0.8, region: Rect | None = None,
                  method: int = cv2.TM_CCOEFF_NORMED) -> MatchResult:
    """Locate `template` inside `image`. Returns best match above threshold."""
    haystack = _crop(image, region)
    th, tw = template.shape[:2]
    if haystack.shape[0] < th or haystack.shape[1] < tw:
        return MatchResult(False, 0.0)
    res = cv2.matchTemplate(haystack, template, method)
    _min_v, max_v, _min_l, max_l = cv2.minMaxLoc(res)
    score = float(max_v)
    if score < threshold:
        return MatchResult(False, score)
    ox, oy = _region_offset(region)
    left, top = max_l[0] + ox, max_l[1] + oy
    return MatchResult(True, score, Rect(left, top, left + tw, top + th))


def find_all_templates(image: np.ndarray, template: np.ndarray,
                       threshold: float = 0.8, region: Rect | None = None,
                       max_results: int = 50,
                       min_dist: int | None = None) -> list[MatchResult]:
    """Find every occurrence of `template` (naive non-max suppression)."""
    haystack = _crop(image, region)
    th, tw = template.shape[:2]
    if haystack.shape[0] < th or haystack.shape[1] < tw:
        return []
    res = cv2.matchTemplate(haystack, template, cv2.TM_CCOEFF_NORMED)
    ys, xs = np.where(res >= threshold)
    cands = sorted(zip(xs.tolist(), ys.tolist()),
                   key=lambda p: float(res[p[1], p[0]]), reverse=True)
    ox, oy = _region_offset(region)
    dist = min_dist if min_dist is not None else max(tw, th) // 2
    kept: list[MatchResult] = []
    taken: list[tuple[int, int]] = []
    for x, y in cands:
        if any(abs(x - kx) < dist and abs(y - ky) < dist for kx, ky in taken):
            continue
        taken.append((x, y))
        left, top = x + ox, y + oy
        kept.append(MatchResult(True, float(res[y, x]),
                                Rect(left, top, left + tw, top + th)))
        if len(kept) >= max_results:
            break
    return kept


def find_template_multiscale(image: np.ndarray, template: np.ndarray,
                             threshold: float = 0.8, region: Rect | None = None,
                             scales=(0.8, 0.9, 1.0, 1.1, 1.2)) -> MatchResult:
    """Template match across several template scales; return the best hit.

    Useful when a script's reference image was captured at a different DPI.
    """
    best = MatchResult(False, 0.0)
    for s in scales:
        if s == 1.0:
            scaled = template
        else:
            scaled = cv2.resize(template, None, fx=s, fy=s,
                                interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
        r = find_template(image, scaled, threshold=0.0, region=region)
        if r.score > best.score:
            best = r
    best.found = best.score >= threshold
    if not best.found:
        best.rect = None
    return best


# -- colour operations (找色 / 比色) -----------------------------------------
def _rgb_to_bgr(rgb: tuple[int, int, int]) -> np.ndarray:
    r, g, b = rgb
    return np.array([b, g, r], dtype=np.int16)


def get_pixel(image: np.ndarray, x: int, y: int) -> tuple[int, int, int]:
    """Return the RGB colour at (x, y)."""
    b, g, r = image[y, x][:3]
    return (int(r), int(g), int(b))


def _color_mask(image: np.ndarray, rgb: tuple[int, int, int],
                tolerance: int, region: Rect | None) -> tuple[np.ndarray, int, int]:
    hay = _crop(image, region).astype(np.int16)
    target = _rgb_to_bgr(rgb)
    diff = np.abs(hay[:, :, :3] - target)
    mask = np.all(diff <= tolerance, axis=2)
    ox, oy = _region_offset(region)
    return mask, ox, oy


def find_color(image: np.ndarray, rgb: tuple[int, int, int],
               tolerance: int = 12, region: Rect | None = None) -> Point | None:
    """Return the first (top-left-most) pixel matching `rgb` within tolerance."""
    mask, ox, oy = _color_mask(image, rgb, tolerance, region)
    hits = np.argwhere(mask)
    if hits.size == 0:
        return None
    y, x = hits[0]
    return Point(int(x) + ox, int(y) + oy)


def count_color(image: np.ndarray, rgb: tuple[int, int, int],
                tolerance: int = 12, region: Rect | None = None) -> int:
    """Count pixels matching `rgb` (useful for threshold/health-bar checks)."""
    mask, _ox, _oy = _color_mask(image, rgb, tolerance, region)
    return int(mask.sum())


def find_best(image: np.ndarray, template: np.ndarray,
              thresholds=(0.95, 0.9, 0.85, 0.8), region: Rect | None = None,
              multiscale: bool = False) -> tuple[float, MatchResult]:
    """Confidence-adaptive match: try descending thresholds, stop at first hit.

    Returns (threshold_used, MatchResult). Lets a script prefer a high-confidence
    match but still accept a looser one, and know how confident it had to be.
    """
    for th in sorted(thresholds, reverse=True):
        res = (find_template_multiscale(image, template, th, region) if multiscale
               else find_template(image, template, th, region))
        if res.found:
            return float(th), res
    # Nothing matched even at the loosest threshold; report the best score seen.
    res = find_template(image, template, 0.0, region)
    res.found = False
    res.rect = None
    return 0.0, res


def find_template_masked(image: np.ndarray, template: np.ndarray,
                         mask: np.ndarray, threshold: float = 0.85,
                         region: Rect | None = None) -> MatchResult:
    """Template match ignoring masked-out pixels (mask==0 pixels are ignored).

    Lets a template have transparent/irrelevant areas (rounded corners, dynamic
    text) — only the mask!=0 pixels contribute. Uses TM_CCORR_NORMED, which
    OpenCV supports with a mask.
    """
    haystack = _crop(image, region)
    th, tw = template.shape[:2]
    if haystack.shape[0] < th or haystack.shape[1] < tw:
        return MatchResult(False, 0.0)
    res = cv2.matchTemplate(haystack, template, cv2.TM_CCORR_NORMED, mask=mask)
    res = np.nan_to_num(res, nan=0.0, posinf=0.0, neginf=0.0)
    _min_v, max_v, _min_l, max_l = cv2.minMaxLoc(res)
    score = float(max_v)
    if score < threshold:
        return MatchResult(False, score)
    ox, oy = _region_offset(region)
    left, top = max_l[0] + ox, max_l[1] + oy
    return MatchResult(True, score, Rect(left, top, left + tw, top + th))


def find_any(image: np.ndarray, templates: dict[str, np.ndarray],
             threshold: float = 0.85, region: Rect | None = None) -> tuple[str | None, MatchResult]:
    """Find the best match among several named templates.

    Returns (name, MatchResult); name is None if none passed threshold.
    """
    best_name: str | None = None
    best = MatchResult(False, 0.0)
    for name, tpl in templates.items():
        r = find_template(image, tpl, threshold=0.0, region=region)
        if r.score > best.score:
            best, best_name = r, name
    if best.score < threshold:
        best.found = False
        best.rect = None
        return None, best
    best.found = True
    return best_name, best


# -- HSV colour range (更鲁棒的找色) -----------------------------------------
def _hsv(image: np.ndarray, region: Rect | None):
    hay = _crop(image, region)
    return cv2.cvtColor(hay, cv2.COLOR_BGR2HSV)


def in_range_mask(image: np.ndarray, hsv_low: tuple[int, int, int],
                  hsv_high: tuple[int, int, int],
                  region: Rect | None = None) -> np.ndarray:
    """Boolean mask of pixels within an HSV range (OpenCV H:0-179, S/V:0-255)."""
    hsv = _hsv(image, region)
    lo = np.array(hsv_low, dtype=np.uint8)
    hi = np.array(hsv_high, dtype=np.uint8)
    return cv2.inRange(hsv, lo, hi).astype(bool)


def find_color_hsv(image: np.ndarray, hsv_low, hsv_high,
                   region: Rect | None = None) -> Point | None:
    """First pixel within an HSV range — robust to brightness/anti-aliasing."""
    mask = in_range_mask(image, hsv_low, hsv_high, region)
    hits = np.argwhere(mask)
    if hits.size == 0:
        return None
    ox, oy = _region_offset(region)
    y, x = hits[0]
    return Point(int(x) + ox, int(y) + oy)


def color_ratio(image: np.ndarray, rgb: tuple[int, int, int],
                tolerance: int = 20, region: Rect | None = None) -> float:
    """Fraction (0..1) of pixels in `region` matching `rgb`.

    Handy for reading a progress/health bar's fill level: point `region` at the
    bar and the ratio approximates how full it is.
    """
    mask, _ox, _oy = _color_mask(image, rgb, tolerance, region)
    total = mask.size
    return float(mask.sum()) / total if total else 0.0


def match_multi_color(image: np.ndarray, anchor: Point,
                      anchor_rgb: tuple[int, int, int],
                      offsets: list[tuple[int, int, tuple[int, int, int]]],
                      tolerance: int = 12) -> bool:
    """自动精灵-style 多点比色.

    Verify the anchor pixel matches `anchor_rgb` AND every (dx, dy, rgb) offset
    pixel (relative to the anchor) matches its expected colour. This is the
    classic robust "is this exact UI state on screen" check.
    """
    h, w = image.shape[:2]

    def ok(px: int, py: int, rgb: tuple[int, int, int]) -> bool:
        if not (0 <= px < w and 0 <= py < h):
            return False
        r, g, b = get_pixel(image, px, py)
        er, eg, eb = rgb
        return (abs(r - er) <= tolerance and abs(g - eg) <= tolerance
                and abs(b - eb) <= tolerance)

    if not ok(anchor.x, anchor.y, anchor_rgb):
        return False
    return all(ok(anchor.x + dx, anchor.y + dy, rgb) for dx, dy, rgb in offsets)
