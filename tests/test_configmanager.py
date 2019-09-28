from configparser import ConfigParser
from multiprocessing import cpu_count

import pytest

from inspectortiger.configmanager import ConfigManager


@pytest.fixture
def parser():
    parser = ConfigParser()
    parser["Config inspectortiger"] = dict.fromkeys(("ignore", "workers"), "-")
    return parser


@pytest.fixture
def manager(mocker, tmp_path, parser):
    cfg = tmp_path / "config.ini"
    mocker.patch("inspectortiger.configmanager.USER_CONFIG", cfg)
    with open(cfg, "w") as config:
        parser.write(config)
    manager = ConfigManager()
    return manager


def test_configmanager_start(parser, tmp_path, mocker):
    cfg = tmp_path / "config.ini"
    mocker.patch("inspectortiger.configmanager.USER_CONFIG", cfg)
    manager = ConfigManager()
    assert "tmpkey" not in manager.defaults

    with open(cfg, "w") as config:
        parser.write(config)

    manager = ConfigManager()
    assert "ignore" in manager.defaults


def test_configmanager_discover(manager):
    plugins = ("foo", "bar", "baz")
    for plugin in plugins:
        manager.config[f"Plugins {plugin}"] = {f"epic_{plugin}": f"itplugin_{plugin}"}

    namespace = manager.discover()
    for plugin in plugins:
        assert plugin in namespace
        assert namespace[plugin] == {f"epic_{plugin}": f"itplugin_{plugin}"}


def test_configmanager_ignore_no(manager):
    del manager.defaults["ignore"]
    assert manager.ignore == ()


def test_configmanager_ignore_single(manager):
    manager.defaults["ignore"] = "abc"
    assert manager.ignore == ("ABC",)


def test_configmanager_ignore_multiple(manager):
    manager.defaults["ignore"] = "abc, dce"
    assert manager.ignore == ("ABC", "DCE")


def test_configmanager_workers_no(manager):
    del manager.defaults["workers"]
    assert manager.workers == cpu_count()


def test_configmanager_workers_max(manager):
    manager.defaults["workers"] = "max"
    assert manager.workers == cpu_count()


def test_configmanager_workers_digit(manager):
    manager.defaults["workers"] = "5"
    assert manager.workers == 5
