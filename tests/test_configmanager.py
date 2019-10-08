import sys
from types import ModuleType

import pytest

from inspectortiger.configmanager import (
    Blacklist,
    Config,
    ConfigManager,
    Plugin,
    PluginLoadError,
    _Plugin,
)
from inspectortiger.utils import mark


def test_plugin_metaclass():
    MyPlugin = _Plugin(
        "My Plugin", (), {"__init__": lambda *args, **kwargs: None}
    )
    assert MyPlugin(1, 2) is MyPlugin(1, 2)
    assert MyPlugin(1, 3) is not MyPlugin(1, 4)

    first = MyPlugin(1, 5)
    first.active = True
    assert MyPlugin(1, 5).active


def test_plugin_init():
    package = Plugin("b", "a")
    assert package.plugin == "b" and package.namespace == "a"
    assert package.static_name == "a.b"
    assert str(package) == "b"

    sub_package = Plugin("c", "a.b")
    assert sub_package.plugin == "c" and sub_package.namespace == "a.b"
    assert sub_package.static_name == "a.b.c"
    assert str(sub_package) == "c"

    sub_sub_package = Plugin("d", "a.b.c")
    assert (
        sub_sub_package.plugin == "d" and sub_sub_package.namespace == "a.b.c"
    )
    assert sub_sub_package.static_name == "a.b.c.d"
    assert str(sub_sub_package) == "d"


def test_plugin_from_simple():
    assert Plugin.from_simple("a.b") is Plugin("b", "a")
    assert Plugin.from_simple("a.b.c") is Plugin("c", "a.b")
    assert Plugin.from_simple("a.b.c.d") is Plugin("d", "a.b.c")

    core_package = Plugin.from_simple("@context")
    assert (
        core_package.plugin == "context"
        and core_package.namespace == "inspectortiger.plugins"
    )
    sub_core_package = Plugin.from_simple("@community.unimport")
    assert (
        sub_core_package.plugin == "unimport"
        and sub_core_package.namespace == "inspectortiger.plugins.community"
    )


def test_plugin_from_config():
    plugins = Plugin.from_config(dict(a=["b", "c.d"]))
    assert isinstance(plugins, list)
    assert plugins[0] is Plugin("b", "a")
    assert plugins[1] is Plugin("d", "a.c")
    multiple_namespace_plugins = Plugin.from_config(dict(a=["b"], c=["d.e"]))
    assert multiple_namespace_plugins[0] is Plugin("b", "a")
    assert multiple_namespace_plugins[1] is Plugin("e", "c.d")


def test_plugin_require():
    dummy = lambda: None

    Plugin.require("b", "a")(dummy)
    assert hasattr(dummy, "requires")
    assert isinstance(dummy.requires, list)
    assert len(dummy.requires) == 1
    assert Plugin("b", "a") in dummy.requires

    Plugin.require("a.b.c")(dummy)
    assert len(dummy.requires) == 2
    assert Plugin("c", "a.b") in dummy.requires


def test_plugin_load(mocker):
    plugin = Plugin("a", "b")
    import_module = mocker.patch("importlib.import_module")
    plugin.load()
    import_module.assert_called_with(plugin.static_name)

    import_module.side_effect = ImportError
    with pytest.raises(PluginLoadError):
        plugin.load()

    import_module.reset_mock(side_effect=True)
    import_module.return_value = ModuleType("my_module")
    plugin.load()


def test_plugin_load_py_version(mocker):
    class Module(ModuleType):
        __py_version__ = (1, 0)

    sys.modules["my_fake_module"] = module = Module("my_module")
    plugin = Plugin("my_fake_module", "", static_name="my_fake_module")
    pyv = sys.version_info

    plugin.load()
    assert plugin.python_version == module.__py_version__
    assert plugin.inactive is False

    module.__py_version__ = (pyv.major, pyv.minor + 1)
    plugin.load()
    assert plugin.python_version == module.__py_version__
    assert plugin.inactive

    module.some_actionable = actionable = lambda: dummy
    mark(actionable)
    plugin.load()
    assert actionable.plugin is plugin


def test_blacklist():
    blacklist = Blacklist(
        ["a.b.c.d", Plugin("b", "a"), "a.b.c"], ["X", "Y", "Z"]
    )
    assert Plugin.from_simple("a.b.c.d") in blacklist.plugins
    assert Plugin("b", "a") in blacklist.plugins
    assert Plugin.from_simple("a.b.c") in blacklist.plugins
    assert all((item in blacklist.codes) for item in {"X", "Y", "Z"})


def test_config():
    config = Config(plugins=dict(a=["b", "c.d"]))
    assert config.plugins[0] is Plugin("b", "a")
    assert config.plugins[1] is Plugin("d", "a.c")

    config = Config(
        blacklist=dict(plugins=["a.b.c.d", Plugin("b", "a"), "a.b.c"])
    )
    assert len(config.blacklist.plugins) == 3
    assert all(
        isinstance(plugin, Plugin) for plugin in config.blacklist.plugins
    )


@pytest.mark.parametrize(
    "cfg",
    [
        {"workers": 0xFF},
        {"logging_level": 50, "fail_exit": False},
        {"plugins": dict(a=["b", "c.d"])},
        {
            "plugins": dict(a=["b", "c.d"]),
            "blacklist": dict(plugins=["a.b.c.d", Plugin("b", "a"), "a.b.c"]),
        },
    ],
)
def test_configmanager(mocker, cfg):
    parser = mocker.patch(
        "inspectortiger.configmanager.ConfigManager._parse_config"
    )
    parser.return_value = {}
    assert ConfigManager().config == Config()

    parser.return_value = cfg
    assert ConfigManager().config == Config(**cfg)


def test_configmanager_parse(tmp_path):
    config = tmp_path / "cfg.json"
    assert ConfigManager._parse_config(config) == {}
    config.write_text("{'a': invaliDJSON}")
    assert ConfigManager._parse_config(config) == {}

    other_config = tmp_path / "other_cfg.json"
    other_config.write_text('{"valid": "json"}')
    assert ConfigManager._parse_config(other_config) == {"valid": "json"}
