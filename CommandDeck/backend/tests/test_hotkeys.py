from command_deck.hotkeys import MultiPressDetector


def test_third_press_triggers_and_resets():
    detector = MultiPressDetector(3, 1.2)
    assert detector.register_press("F13", 10.0) == (1, False)
    assert detector.register_press("F13", 10.3) == (2, False)
    assert detector.register_press("F13", 10.6) == (3, True)
    assert detector.register_press("F13", 10.8) == (1, False)


def test_old_press_expires():
    detector = MultiPressDetector(3, 1.0)
    detector.register_press("F14", 20.0)
    detector.register_press("F14", 20.4)
    assert detector.register_press("F14", 21.1) == (2, False)
