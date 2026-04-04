from backend.services.vision_card_extract import parse_model_json_response


def test_parse_model_json_response_strips_fence() -> None:
    text = """```json
{"player_name": "A", "card_number": "1", "card_year": 2023, "parallel_or_insert": "Base"}
```"""
    d = parse_model_json_response(text)
    assert d["player_name"] == "A"
    assert d["card_year"] == 2023
