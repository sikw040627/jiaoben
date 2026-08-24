from autoauto.getevent import parse_getevent


def _tap_lines():
    # A short touch that barely moves -> tap.
    return [
        "[   1000.000000] /dev/input/event3 EV_KEY BTN_TOUCH DOWN",
        "[   1000.000000] /dev/input/event3 EV_ABS ABS_MT_POSITION_X 000000c8",  # 200
        "[   1000.000000] /dev/input/event3 EV_ABS ABS_MT_POSITION_Y 00000190",  # 400
        "[   1000.000000] /dev/input/event3 EV_SYN SYN_REPORT 00000000",
        "[   1000.050000] /dev/input/event3 EV_KEY BTN_TOUCH UP",
    ]


def _swipe_lines():
    return [
        "[   2000.000000] /dev/input/event3 EV_KEY BTN_TOUCH DOWN",
        "[   2000.000000] /dev/input/event3 EV_ABS ABS_MT_POSITION_X 00000064",  # 100
        "[   2000.000000] /dev/input/event3 EV_ABS ABS_MT_POSITION_Y 00000064",  # 100
        "[   2000.000000] /dev/input/event3 EV_SYN SYN_REPORT 00000000",
        "[   2000.100000] /dev/input/event3 EV_ABS ABS_MT_POSITION_X 000001f4",  # 500
        "[   2000.100000] /dev/input/event3 EV_ABS ABS_MT_POSITION_Y 00000064",
        "[   2000.100000] /dev/input/event3 EV_SYN SYN_REPORT 00000000",
        "[   2000.300000] /dev/input/event3 EV_KEY BTN_TOUCH UP",
    ]


def test_parse_tap():
    acts = parse_getevent(_tap_lines())
    assert len(acts) == 1
    a = acts[0]
    assert a.kind == "tap"
    assert a.params == {"x": 200, "y": 400}


def test_parse_swipe():
    acts = parse_getevent(_swipe_lines())
    assert len(acts) == 1
    a = acts[0]
    assert a.kind == "swipe"
    assert a.params["x1"] == 100 and a.params["x2"] == 500
    assert a.params["duration_ms"] == 300


def test_parse_tracking_id_lift():
    # protocol-B style using ABS_MT_TRACKING_ID for down/up
    lines = [
        "[   3000.000000] /dev/input/event3 EV_ABS ABS_MT_TRACKING_ID 0000004d",
        "[   3000.000000] /dev/input/event3 EV_ABS ABS_MT_POSITION_X 00000032",  # 50
        "[   3000.000000] /dev/input/event3 EV_ABS ABS_MT_POSITION_Y 00000032",  # 50
        "[   3000.000000] /dev/input/event3 EV_SYN SYN_REPORT 00000000",
        "[   3000.040000] /dev/input/event3 EV_ABS ABS_MT_TRACKING_ID ffffffff",
    ]
    acts = parse_getevent(lines)
    assert len(acts) == 1
    assert acts[0].kind == "tap"
    assert acts[0].params == {"x": 50, "y": 50}


def test_scale_applied():
    acts = parse_getevent(_tap_lines(), scale_x=0.5, scale_y=0.5)
    assert acts[0].params == {"x": 100, "y": 200}
