import json

from data.raw_writer import RawWriter


def test_envelope_has_contract_fields_and_redacts_secret(tmp_path):
    writer = RawWriter(tmp_path)
    event = writer.write(
        transport="REST", endpoint_or_channel="/api/v3/data/masterdata",
        payload={"data": [], "token": "do-not-store", "apiSecret": "do-not-store"},
        http_status=200,
    )
    assert event["transport"] == "REST"
    assert event["provider"] == "SSI" and event["source"] == "SSI_FASTCONNECT"
    assert event["mode"] == "SYNTHETIC_TEST"
    assert event["payload"]["token"] == "[REDACTED]"
    assert event["payload"]["apiSecret"] == "[REDACTED]"
    output = next((tmp_path / "rest").glob("*.jsonl"))
    saved = json.loads(output.read_text().strip())
    assert saved["payload_hash"] == event["payload_hash"]


def test_append_preserves_existing_events(tmp_path):
    writer = RawWriter(tmp_path)
    writer.write(transport="WS", endpoint_or_channel="quote", payload={"type": "quote", "symbol": "SSI"})
    writer.write(transport="WS", endpoint_or_channel="quote", payload={"type": "quote", "symbol": "HPG"})
    output = next((tmp_path / "ws").glob("*.jsonl"))
    assert len(output.read_text().splitlines()) == 2
