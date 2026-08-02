from command_deck.window_focus import _restore_if_minimized


class FakeUser32:
    def __init__(self, *, minimized: bool) -> None:
        self.minimized = minimized
        self.show_calls: list[tuple[int, int]] = []

    def IsIconic(self, _hwnd: int) -> bool:
        return self.minimized

    def ShowWindow(self, hwnd: int, command: int) -> None:
        self.show_calls.append((hwnd, command))


def test_maximized_window_is_not_restored_down() -> None:
    user32 = FakeUser32(minimized=False)

    _restore_if_minimized(user32, 101)

    assert user32.show_calls == []


def test_minimized_window_is_restored_before_focus() -> None:
    user32 = FakeUser32(minimized=True)

    _restore_if_minimized(user32, 101)

    assert user32.show_calls == [(101, 9)]
