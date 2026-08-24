import cv2
import numpy as np

from autoauto.templateset import TemplateSet, scale_template
from conftest import make_template, paste


def test_scale_template_halves():
    tpl = make_template(size=(40, 40))
    scaled = scale_template(tpl, ref_wh=(1080, 1920), dev_wh=(540, 960))
    assert scaled.shape[0] == 20 and scaled.shape[1] == 20


def test_scale_template_identity():
    tpl = make_template(size=(30, 30))
    same = scale_template(tpl, ref_wh=(720, 1280), dev_wh=(720, 1280))
    assert same is tpl  # no resize when ratio is 1:1


def test_templateset_picks_matching_resolution():
    base40 = make_template(color=(0, 200, 0), size=(40, 40))
    small20 = cv2.resize(base40, (20, 20), interpolation=cv2.INTER_AREA)

    scene = np.full((300, 300, 3), 30, dtype=np.uint8)
    paste(scene, small20, x=120, y=90)  # the 20px variant is on screen

    ts = TemplateSet("btn", [base40, small20])
    idx, res = ts.find_indexed(scene, threshold=0.9)
    assert res.found
    assert idx == 1  # the 20px template matched, not the 40px one
    assert res.center.as_tuple() == (130, 100)


def test_templateset_scaled_variants_builder():
    base = make_template(size=(40, 40))
    ts = TemplateSet.scaled_variants("x", base, ref_wh=(1080, 1920),
                                     dev_sizes=[(1080, 1920), (540, 960)])
    assert len(ts.templates) == 2
    assert ts.templates[0].shape[:2] == (40, 40)
    assert ts.templates[1].shape[:2] == (20, 20)


def test_templateset_requires_templates():
    import pytest
    with pytest.raises(ValueError):
        TemplateSet("empty", [])
