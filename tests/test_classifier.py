from unittest.mock import MagicMock

import pytest

from src.classifier import classify


def _make_client(text: str) -> MagicMock:
    client = MagicMock()
    client.messages.create.return_value.content[0].text = text
    return client


def test_classify_simple():
    assert classify("What is 2+2?", client=_make_client("simple")) == "simple"


def test_classify_medium():
    # Confirms strip + lower normalisation
    assert classify("Explain recursion.", client=_make_client(" Medium\n")) == "medium"


def test_classify_hard():
    assert classify("Prove the Riemann hypothesis.", client=_make_client("hard")) == "hard"


def test_classify_invalid_response():
    with pytest.raises(ValueError, match="Unexpected classifier response"):
        classify("What?", client=_make_client("I don't know"))


def test_classify_uses_haiku():
    client = _make_client("simple")
    classify("Hello", client=client)
    call_kwargs = client.messages.create.call_args
    assert call_kwargs.kwargs["model"] == "claude-haiku-4-5-20251001"
