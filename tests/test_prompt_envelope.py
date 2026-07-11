"""Tests for benchmark prompt envelope in the client."""

from simple_token_burner_app.prompt_envelope import (
    measure_max_tokens,
    measure_system_prompt,
    measure_stop_sequences,
)


def test_small_measure_system_requires_one_sentence():
    system = measure_system_prompt("small")
    assert "one short sentence" in system
    assert "bullet" in system.lower()


def test_measure_stop_sequences_nonempty():
    assert measure_stop_sequences()


def test_measure_max_tokens_caps_small():
    assert measure_max_tokens("small", 256) == 80
    assert measure_max_tokens("large", 256) == 256
