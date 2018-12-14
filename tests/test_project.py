# fixture and parameter have the same name
# pylint: disable=redefined-outer-name,useless-super-delegation,protected-access
import json
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rpdk.project import InvalidSettingsError, Project

LANGUAGE = "BQHDBC"
CONTENTS_UTF8 = "💣"


@pytest.fixture
def project():
    return Project()


@contextmanager
def patch_settings(project, data):
    with patch.object(project, "settings_path", autospec=True) as mock_path:
        mock_path.open.return_value.__enter__.return_value = StringIO(data)
        yield mock_path.open


def test_load_settings_invalid_json(project):
    with patch_settings(project, "") as mock_open:
        with pytest.raises(InvalidSettingsError):
            project.load_settings()
    mock_open.assert_called_once_with("r", encoding="utf-8")


def test_load_settings_invalid_settings(project):
    with patch_settings(project, "{}") as mock_open:
        with pytest.raises(InvalidSettingsError):
            project.load_settings()
    mock_open.assert_called_once_with("r", encoding="utf-8")


def test_load_settings_valid_json(project):
    plugin = object()
    type_name = "AWS::Color::Red"

    data = json.dumps({"typeName": type_name, "language": LANGUAGE})
    patch_load = patch("rpdk.project.load_plugin", autospec=True, return_value=plugin)

    with patch_settings(project, data) as mock_open, patch_load as mock_load:
        project.load_settings()

    mock_open.assert_called_once_with("r", encoding="utf-8")
    mock_load.assert_called_once_with(LANGUAGE)
    assert project.type_info == ("AWS", "Color", "Red")
    assert project.type_name == type_name
    assert project._plugin is plugin
    assert project.settings == {}


def test_load_schema_settings_not_loaded(project):
    with pytest.raises(RuntimeError):
        project.load_schema()


def test_load_schema_example(tmpdir):
    project = Project(root=tmpdir)
    project.type_name = "AWS::Color::Blue"
    project._write_example_schema()
    project.load_schema()


def test_overwrite():
    mock_path = MagicMock(spec=Path)
    Project.overwrite(mock_path, LANGUAGE)

    mock_path.open.assert_called_once_with("w", encoding="utf-8")
    mock_f = mock_path.open.return_value.__enter__.return_value
    mock_f.write.assert_called_once_with(LANGUAGE)


def test_safewrite_overwrite(project):
    path = object()
    contents = object()

    patch_attr = patch.object(project, "_overwrite", True)
    patch_meth = patch.object(project, "overwrite", autospec=True)
    with patch_attr, patch_meth as mock_overwrite:
        project.safewrite(path, contents)

    mock_overwrite.assert_called_once_with(path, contents)


def test_safewrite_doesnt_exist(project, tmpdir):
    path = Path(tmpdir.join("test")).resolve()

    with patch.object(project, "_overwrite", False):
        project.safewrite(path, CONTENTS_UTF8)

    with path.open("r", encoding="utf-8") as f:
        assert f.read() == CONTENTS_UTF8


def test_safewrite_exists(project, tmpdir, caplog):
    path = Path(tmpdir.join("test")).resolve()

    with path.open("w", encoding="utf-8") as f:
        f.write(CONTENTS_UTF8)

    with patch.object(project, "_overwrite", False):
        project.safewrite(path, CONTENTS_UTF8)

    last_record = caplog.records[-1]
    assert last_record.levelname == "WARNING"
    assert str(path) in last_record.message


def test_generate(project):
    mock_plugin = MagicMock(spec=["generate"])
    with patch.object(project, "_plugin", mock_plugin):
        project.generate()
    mock_plugin.generate.assert_called_once_with(project)


def test_init(tmpdir):
    type_name = "AWS::Color::Red"

    mock_plugin = MagicMock(spec=["init"])
    patch_load_plugin = patch(
        "rpdk.project.load_plugin", autospec=True, return_value=mock_plugin
    )

    project = Project(root=tmpdir)
    with patch_load_plugin as mock_load_plugin:
        project.init(type_name, LANGUAGE)

    mock_load_plugin.assert_called_once_with(LANGUAGE)
    mock_plugin.init.assert_called_once_with(project)

    assert project.type_info == ("AWS", "Color", "Red")
    assert project.type_name == type_name
    assert project._plugin is mock_plugin
    assert project.settings == {}

    with project.settings_path.open("r", encoding="utf-8") as f:
        assert json.load(f)

    with project.schema_path.open("r", encoding="utf-8") as f:
        assert json.load(f)


def test_package(project):
    expected_arn = "SomeARN"
    expected_template = "template.path"

    mock_plugin = MagicMock(spec=["package"])
    mock_plugin.package.return_value = expected_arn

    with patch.object(project, "_plugin", mock_plugin):
        project.package(expected_template)

    mock_plugin.package.assert_called_once_with(expected_template)
    assert project.handler_arn == expected_arn
