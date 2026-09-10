import math

import pytest

from chad.core.config import GenerationSettings


def test_generation_settings_reject_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        GenerationSettings(temperature=math.inf).validate()


def test_generation_settings_reject_invalid_ranges() -> None:
    with pytest.raises(ValueError):
        GenerationSettings(temperature=0).validate()
    with pytest.raises(ValueError):
        GenerationSettings(top_p=1.1).validate()
    with pytest.raises(ValueError):
        GenerationSettings(max_new_tokens=0).validate()
