import hashlib
import importlib.util
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

import pandas as pd
import pytest


SOURCE_FILES = {
    "clone": ("Extract_CloneCode_Snippets.py",),
    "history": ("Extract_HistoryMetrics&Label.py", "Extract_HistoryMetrics_Label.py"),
    "combine": ("Combine.py",),
}
METRIC_COLUMNS = (
    "cc_lines", "author_count", "modify_count", "avg_added", "avg_deleted",
    "unique_operators", "unique_operands", "total_operators", "total_operands",
)


def pytest_addoption(parser):
    parser.addoption(
        "--source-dir", action="store", default=None,
        help="被测源码目录，默认是 tests 的上级目录。",
    )


def source_directory(config):
    supplied = config.getoption("--source-dir")
    return Path(supplied).resolve() if supplied else Path(__file__).resolve().parent.parent


def source_path(config, module):
    directory = source_directory(config)
    for filename in SOURCE_FILES[module]:
        path = directory / filename
        if path.is_file():
            return path
    raise pytest.UsageError(
        f"源码不存在：{directory} / {SOURCE_FILES[module]}。"
        "请把 tests 放到项目根目录，或明确指定 --source-dir。"
    )


def pytest_report_header(config):
    lines = [f"被测源码目录: {source_directory(config)}"]
    for module in SOURCE_FILES:
        path = source_path(config, module)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{path.name} SHA256={digest}")
    return lines


def pytest_collection_modifyitems(items):
    """把正式用例编号放进 JUnit XML，不额外增加测试数量。"""
    for item in items:
        match = re.match(r"test_(ce|hl|co)_(\d{3})_", item.name)
        if match:
            item.user_properties.append(
                ("case_id", f"CCP-M1-{match[1].upper()}-{match[2]}")
            )


def load_source(config, name):
    path = source_path(config, name)
    spec = importlib.util.spec_from_file_location(f"ccp_test_target_{name}", path)
    if spec is None or spec.loader is None:
        raise pytest.UsageError(f"无法加载源码：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def clone_module(pytestconfig):
    return load_source(pytestconfig, "clone")


@pytest.fixture(scope="session")
def history_module(pytestconfig):
    return load_source(pytestconfig, "history")


@pytest.fixture(scope="session")
def combine_module(pytestconfig):
    return load_source(pytestconfig, "combine")


@pytest.fixture
def sheet_name():
    return "apollo-1.0.0"


@pytest.fixture
def source_file_key(sheet_name):
    # 只是 XML/Excel 匹配键，不在这个路径创建文件。
    def make(filename):
        return f"D:\\download\\{sheet_name}\\{sheet_name}\\{filename}"
    return make


@pytest.fixture
def make_workbook(tmp_path):
    def make(sheets, filename="input.xlsx"):
        path = tmp_path / filename
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            for name, records in sheets.items():
                pd.DataFrame(records).to_excel(writer, sheet_name=name, index=False)
        return path
    return make


@pytest.fixture
def make_clone_xml(tmp_path):
    def make(blocks, filename="clones.xml"):
        root = ET.Element("simian")
        if blocks:
            group = ET.SubElement(root, "set")
            for file, start, end in blocks:
                ET.SubElement(group, "block", {
                    "sourceFile": file,
                    "startLineNumber": str(start),
                    "endLineNumber": str(end),
                })
        path = tmp_path / filename
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
        return path
    return make


@pytest.fixture
def make_commit():
    """根据显式输入创建 XML；不从被测逻辑计算区间或标签。"""
    def make(files=None, message="fix parser bug", author="Alice"):
        root = ET.Element("commit", {"author": author, "hash": "fixture-commit"})
        ET.SubElement(root, "msg").text = message
        if files is not None:
            modified = ET.SubElement(root, "modified_files")
            for record in files:
                file = ET.SubElement(modified, "file", {
                    "old_path": record["path"],
                    "new_path": record["path"],
                    "added_lines": str(record["added"]),
                    "deleted_lines": str(record["deleted"]),
                })
                ET.SubElement(file, "diff").text = record["diff"]
        return minidom.parseString(ET.tostring(root, encoding="utf-8")).documentElement
    return make


@pytest.fixture
def write_commit_xml(tmp_path):
    def write(commits, filename="commits.xml"):
        root = ET.Element("Root")
        for commit in commits:
            root.append(ET.fromstring(commit.toxml()))
        path = tmp_path / filename
        ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
        return path
    return write


@pytest.fixture
def metric_row():
    def make(file, start, end, value=2, bug=0, **overrides):
        row = {"File": file, "cc_start_line": start, "cc_end_line": end}
        row.update({column: value for column in METRIC_COLUMNS})
        row["cc_lines"] = end - start + 1
        row["Bug"] = bug
        row.update(overrides)
        return row
    return make


@pytest.fixture
def assert_result_table():
    def check(actual, expected_records):
        expected = pd.DataFrame(expected_records)
        assert set(actual.columns) == set(expected.columns), "输出列不完整或出现意外列"
        assert len(actual) == len(expected), "输出记录数不符合预期"
        keys = ["File", "cc_start_line", "cc_end_line"]
        actual = actual.sort_values(keys).reset_index(drop=True)
        expected = expected.sort_values(keys).reset_index(drop=True)
        # 身份、区间及标签必须精确；均值允许浮点舍入误差。
        exact = keys + (["Bug"] if "Bug" in expected.columns else [])
        pd.testing.assert_frame_equal(
            actual[exact], expected[exact], check_dtype=False, check_exact=True,
        )
        for column in expected.columns:
            if column not in exact:
                assert actual[column].tolist() == pytest.approx(
                    expected[column].tolist(), rel=1e-9, abs=1e-12,
                ), f"指标 {column} 不符合预期"
    return check
