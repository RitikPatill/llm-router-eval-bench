import json
from unittest.mock import MagicMock

import pytest

from src.eval import RubricScore, judge


def _make_client(text: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value.content[0].text = text
    return client


def test_judge_happy_path():
    payload = json.dumps({"correctness": 4, "coherence": 5, "conciseness": 3})
    score = judge("What is 2+2?", "It is 4.", client=_make_client(payload))
    assert isinstance(score, RubricScore)
    assert score.correctness == 4
    assert score.coherence == 5
    assert score.conciseness == 3


def test_judge_out_of_range_raises():
    payload = json.dumps({"correctness": 7, "coherence": 5, "conciseness": 3})
    with pytest.raises(ValueError, match="out of range"):
        judge("Hello", "Hi there.", client=_make_client(payload))


def test_judge_non_json_raises():
    with pytest.raises(ValueError, match="unparseable"):
        judge("Hello", "Hi.", client=_make_client("Sorry, I cannot score this."))


def test_judge_missing_key_raises():
    payload = json.dumps({"correctness": 3, "coherence": 4})  # missing conciseness
    with pytest.raises(ValueError, match="unparseable"):
        judge("Hello", "Hi.", client=_make_client(payload))


def test_judge_uses_haiku_by_default():
    payload = json.dumps({"correctness": 5, "coherence": 5, "conciseness": 5})
    client = _make_client(payload)
    judge("What is the sky?", "Blue.", client=client)
    call_kwargs = client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == "claude-haiku-4-5-20251001"


def test_judge_float_scores_cast_to_int():
    # JSON floats like 4.0 should be accepted and cast to int
    payload = json.dumps({"correctness": 4.0, "coherence": 5.0, "conciseness": 3.0})
    score = judge("What is 2+2?", "4", client=_make_client(payload))
    assert score.correctness == 4
    assert isinstance(score.correctness, int)
