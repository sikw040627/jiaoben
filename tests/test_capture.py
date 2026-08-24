import numpy as np

from autoauto.capture import ScreenCache, crop, decode_png
from autoauto.geometry import Rect
from conftest import FakeClock, FakeDevice


def test_decode_png_round_trip(device):
    png = device.screencap_png()
    img = decode_png(png)
    assert img.shape == (device._h, device._w, 3)


def test_crop_region():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[10:20, 30:40] = 255
    c = crop(img, Rect(30, 10, 40, 20))
    assert c.shape == (10, 10, 3)
    assert int(c.mean()) == 255


def test_screencache_ttl_caches_frame():
    clk = FakeClock()
    dev = FakeDevice()
    grabbed = {"n": 0}
    orig = dev.screencap_png

    def counting():
        grabbed["n"] += 1
        return orig()

    dev.screencap_png = counting
    cache = ScreenCache(dev, ttl=1.0, clock=clk)

    cache.grab()            # miss -> grab (n=1)
    cache.grab()            # within ttl -> cached (still 1)
    assert grabbed["n"] == 1

    clk.advance(1.5)        # past ttl
    cache.grab()            # miss -> grab (n=2)
    assert grabbed["n"] == 2

    cache.grab(force=True)  # forced -> grab (n=3)
    assert grabbed["n"] == 3
