import os
import pytest
import importlib, config
import config




def test_skill_id_loaded(monkeypatch):
    monkeypatch.setenv("SKILL_ID", "amzn1.ask.skill.test")
    monkeypatch.setenv("ENDPOINT_TOKEN", "test-token")
    monkeypatch.setenv("PORT", "8000")
    importlib.reload(config)
    assert config.SKILL_ID == "amzn1.ask.skill.test"
    assert config.PORT == 8000

def test_apps_json_loads():
    assert isinstance(config.APPS, dict)
    assert "chrome" in config.APPS

