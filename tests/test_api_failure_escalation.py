from pathlib import Path

from fpv_board.main import _update_failure_escalation
from fpv_board.state.state_store import StateStore


def test_api_failure_escalation_counts(tmp_path: Path, monkeypatch):
    sent = []

    def fake_send_warning(config_path, msg):
        sent.append(msg)

    monkeypatch.setattr("fpv_board.main._send_warning_email", fake_send_warning)

    store = StateStore(tmp_path / "state.json")
    cfg = tmp_path / "fpv_board" / "config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("{}", encoding="utf-8")

    for _ in range(42):
        _update_failure_escalation(store, daylight_failure=True, config_path=cfg)

    assert len(sent) == 4
