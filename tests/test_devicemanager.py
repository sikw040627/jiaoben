import pytest

from autoauto.devicemanager import call_with_retries


def test_succeeds_first_try():
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        return "ok"

    assert call_with_retries(fn, attempts=3, sleep=lambda d: None) == "ok"
    assert calls["n"] == 1


def test_succeeds_after_failures_and_recovers():
    calls = {"n": 0}
    recovered = []

    def fn():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return 42

    slept = []
    result = call_with_retries(fn, attempts=5, delay=0.5,
                               recover=lambda e: recovered.append(str(e)),
                               sleep=slept.append)
    assert result == 42
    assert calls["n"] == 3
    assert recovered == ["transient", "transient"]
    assert slept == [0.5, 0.5]


def test_exhausts_and_reraises():
    def fn():
        raise ValueError("always")

    with pytest.raises(ValueError, match="always"):
        call_with_retries(fn, attempts=2, sleep=lambda d: None)
