import numpy as np

from autoauto.ocr import preprocess_for_digits


def test_preprocess_scales_and_binarizes():
    img = np.random.randint(0, 255, (10, 20, 3), dtype=np.uint8)
    out = preprocess_for_digits(img, scale=2.0)
    assert out.shape == (20, 40)          # scaled 2x
    assert out.ndim == 2                  # single channel
    assert set(np.unique(out)).issubset({0, 255})  # binary


def test_preprocess_no_scale():
    img = np.full((8, 8, 3), 100, dtype=np.uint8)
    out = preprocess_for_digits(img, scale=1.0)
    assert out.shape == (8, 8)


def test_preprocess_invert():
    img = np.zeros((6, 6, 3), dtype=np.uint8)
    img[:, :3] = 255  # half white
    a = preprocess_for_digits(img, scale=1.0, invert=False)
    b = preprocess_for_digits(img, scale=1.0, invert=True)
    assert np.array_equal(b, 255 - a)  # inversion flips the binary image
