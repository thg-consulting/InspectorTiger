import ast
from unittest.mock import Mock

import pytest

from inspectortiger import Inspector
from inspectortiger.reports import Report
from inspectortiger.utils import Events


def test_inspector_triggerer():
    dummy = Mock()
    Inspector.register(ast.Expr)(dummy)
    assert dummy in Inspector._hooks[ast.Expr]
    Inspector.register(Events.INITAL)(dummy)
    assert dummy in Inspector._event_hooks[Events.INITAL]
    with pytest.raises(ValueError):
        Inspector.register(None)(dummy)


def test_inspector_events_initalization():
    dummy = Mock()
    Inspector.register(Events.INITAL)(dummy)
    Inspector(None)
    dummy.assert_called_once()


def test_inspector_visit():
    dummy = Mock()
    dummy.__name__ = "dummy"
    dummy.plugin = "dummy"
    Inspector.register(ast.Name)(dummy)
    inspector = Inspector(None)
    visitor = inspector.visit_Name
    assert dummy in visitor.args[0]
    visitor(ast.parse("xyz", "<ast>", "eval").body)
    dummy.assert_called_once()
    assert (
        Report(filename="None", lineno=1, code="DUMMY")
        in inspector.results[dummy.plugin]
    )


def test_attribute_error():
    inspector = Inspector(None)
    with pytest.raises(AttributeError):
        inspector.blabla()
