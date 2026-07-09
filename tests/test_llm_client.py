import pytest

from llm_client import FakeLLMClient, _extract_json


def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_markdown_fences():
    raw = '```json\n{"a": 1, "b": "x"}\n```'
    assert _extract_json(raw) == {"a": 1, "b": "x"}


def test_extract_json_with_surrounding_prose():
    raw = 'Sure, here you go:\n{"a": 1}\nHope that helps!'
    assert _extract_json(raw) == {"a": 1}


def test_fake_llm_returns_scripted_responses_in_order():
    llm = FakeLLMClient(responses=["first", "second"])
    assert llm.generate_text("p1") == "first"
    assert llm.generate_text("p2") == "second"


def test_fake_llm_falls_back_to_default_when_exhausted():
    llm = FakeLLMClient(responses=["only one"], default_response="fallback")
    assert llm.generate_text("p1") == "only one"
    assert llm.generate_text("p2") == "fallback"
    assert llm.generate_text("p3") == "fallback"


def test_fake_llm_records_calls():
    llm = FakeLLMClient()
    llm.generate_text("hello", system="sys")
    assert llm.calls == [{"prompt": "hello", "system": "sys"}]


def test_call_structured_retries_on_malformed_json():
    llm = FakeLLMClient(responses=["not json at all", '{"ok": true}'])
    result = llm.call_structured("prompt", retries=1)
    assert result == {"ok": True}


def test_call_structured_raises_after_exhausting_retries():
    llm = FakeLLMClient(responses=["nope", "still nope"])
    with pytest.raises(ValueError):
        llm.call_structured("prompt", retries=1)
