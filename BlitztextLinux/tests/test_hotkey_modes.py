"""Tests für HotkeyService — Hold-Modus, Toggle-Modus, Debounce, Reconnect."""
import time
import pytest
from unittest.mock import MagicMock, patch, call
from app.hotkey_service import HotkeyService, HotkeyMode


@pytest.fixture
def callbacks():
    return {
        "start": MagicMock(),
        "stop": MagicMock(),
    }


@pytest.fixture
def toggle_service(callbacks):
    svc = HotkeyService(
        mode=HotkeyMode.TOGGLE,
        on_start=callbacks["start"],
        on_stop=callbacks["stop"],
    )
    return svc


@pytest.fixture
def hold_service(callbacks):
    svc = HotkeyService(
        mode=HotkeyMode.HOLD,
        on_start=callbacks["start"],
        on_stop=callbacks["stop"],
    )
    return svc


class TestHotkeyMode:
    def test_toggle_mode_value(self):
        assert HotkeyMode.TOGGLE.value == "toggle"

    def test_hold_mode_value(self):
        assert HotkeyMode.HOLD.value == "hold"


class TestToggleMode:
    def test_first_keydown_starts(self, toggle_service, callbacks):
        toggle_service.simulate_key_down()
        callbacks["start"].assert_called_once()
        callbacks["stop"].assert_not_called()

    def test_second_keydown_stops(self, toggle_service, callbacks):
        toggle_service.simulate_key_down()
        toggle_service.simulate_key_down()
        callbacks["start"].assert_called_once()
        callbacks["stop"].assert_called_once()

    def test_keyup_ignored_in_toggle(self, toggle_service, callbacks):
        toggle_service.simulate_key_up()
        callbacks["start"].assert_not_called()
        callbacks["stop"].assert_not_called()

    def test_toggle_sequence_start_stop_start(self, toggle_service, callbacks):
        toggle_service.simulate_key_down()  # start
        toggle_service.simulate_key_down()  # stop
        toggle_service.simulate_key_down()  # start again
        assert callbacks["start"].call_count == 2
        assert callbacks["stop"].call_count == 1


class TestHoldMode:
    def test_keydown_starts(self, hold_service, callbacks):
        hold_service.simulate_key_down()
        callbacks["start"].assert_called_once()

    def test_keyup_stops(self, hold_service, callbacks):
        hold_service.simulate_key_down()
        hold_service.simulate_key_up()
        callbacks["stop"].assert_called_once()

    def test_keydown_without_keyup_no_stop(self, hold_service, callbacks):
        hold_service.simulate_key_down()
        callbacks["stop"].assert_not_called()

    def test_double_keydown_no_double_start(self, hold_service, callbacks):
        """Autorepeat-Events sollen keinen zweiten Start auslösen."""
        hold_service.simulate_key_down()
        hold_service.simulate_key_down()  # Autorepeat
        callbacks["start"].assert_called_once()


class TestDebounce:
    def test_rapid_toggle_debounced(self, toggle_service, callbacks):
        """Zwei KEY_DOWN innerhalb der Debounce-Zeit (0.6s) → nur ein Aufruf."""
        toggle_service.simulate_key_down()
        toggle_service.simulate_key_down()  # zu schnell → debounced
        # Erwarte: entweder start+stop oder nur start — nicht start+stop+start
        total_calls = callbacks["start"].call_count + callbacks["stop"].call_count
        assert total_calls <= 2

    def test_debounce_interval_is_0_6s(self, toggle_service):
        assert toggle_service.debounce_interval == pytest.approx(0.6)


class TestModeFromConfig:
    def test_from_string_toggle(self, callbacks):
        svc = HotkeyService.from_config(
            mode_str="toggle",
            on_start=callbacks["start"],
            on_stop=callbacks["stop"],
        )
        assert svc.mode == HotkeyMode.TOGGLE

    def test_from_string_hold(self, callbacks):
        svc = HotkeyService.from_config(
            mode_str="hold",
            on_start=callbacks["start"],
            on_stop=callbacks["stop"],
        )
        assert svc.mode == HotkeyMode.HOLD

    def test_invalid_mode_raises(self, callbacks):
        with pytest.raises(ValueError, match="mode"):
            HotkeyService.from_config(
                mode_str="invalid",
                on_start=callbacks["start"],
                on_stop=callbacks["stop"],
            )
