import pytest
import yaml

from src.router import Router, RouteTarget


def test_route_simple():
    router = Router()
    target = router.route("simple")
    assert target.model == "claude-haiku-4-5-20251001"


def test_route_medium():
    router = Router()
    target = router.route("medium")
    assert target.model == "claude-sonnet-4-6"
    assert target.provider == "anthropic"


def test_route_hard():
    router = Router()
    target = router.route("hard")
    assert target.max_cost_usd == 0.20


def test_route_unknown_label():
    router = Router()
    with pytest.raises(KeyError):
        router.route("extreme")  # type: ignore[arg-type]


def test_router_reads_custom_path(tmp_path):
    config = {
        "routing": {
            "simple": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "max_cost_usd": 0.001,
            }
        }
    }
    config_file = tmp_path / "routing.yaml"
    config_file.write_text(yaml.dump(config))

    router = Router(config_path=config_file)
    target = router.route("simple")
    assert target.provider == "openai"
    assert target.model == "gpt-4o-mini"
    assert target.max_cost_usd == 0.001
