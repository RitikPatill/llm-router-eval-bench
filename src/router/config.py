from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

# Default config is resolved relative to this file so it works regardless of CWD.
_DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "config" / "routing.yaml"


@dataclass
class RouteTarget:
    provider: str
    model: str
    max_cost_usd: float | None


class Router:
    def __init__(self, config_path: str | Path = _DEFAULT_CONFIG) -> None:
        with open(config_path) as fh:
            data = yaml.safe_load(fh)
        self._routing: dict[str, dict] = data["routing"]

    def route(self, label: Literal["simple", "medium", "hard"]) -> RouteTarget:
        tier = self._routing[label]  # raises KeyError for unknown labels
        return RouteTarget(
            provider=tier["provider"],
            model=tier["model"],
            max_cost_usd=tier.get("max_cost_usd"),
        )
