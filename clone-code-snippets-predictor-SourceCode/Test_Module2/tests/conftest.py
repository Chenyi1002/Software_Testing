"""模块二测试公共配置：加载 Halstead 度量提取相关源码，提供临时数据 fixture。

被测源码：
- SourceCode/Halstead_parser_code/code_halstead_extract.py（HalsteadMetrics 分析器）
- SourceCode/Extract_HalsteadMetrics.py（Excel 读取与度量写回）
"""
import hashlib
import importlib.util
from pathlib import Path
import re

import pandas as pd
import pytest


SOURCE_DIR_DEFAULT = Path(__file__).resolve().parent.parent.parent
SOURCE_FILES = {
    "halstead_parser": ("SourceCode/Halstead_parser_code/code_halstead_extract.py",),
    "extract_metrics": ("SourceCode/Extract_HalsteadMetrics.py",),
}
# 让 Extract_HalsteadMetrics.py 内部的相对导入可用
IMPORT_ROOT = "SourceCode"


def pytest_addoption(parser):
    parser.addoption(
        "--source-dir", action="store", default=None,
        help="被测源码目录，默认是 tests 的上级目录。",
    )


def source_directory(config):
    supplied = config.getoption("--source-dir")
    return Path(supplied).resolve() if supplied else SOURCE_DIR_DEFAULT


def source_path(config, module):
    directory = source_directory(config)
    rel = SOURCE_FILES[module][0]
    path = directory / rel
    if not path.is_file():
        raise pytest.UsageError(f"源码不存在：{path}")
    return path


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
        match = re.match(r"test_(hm|ex)_(\d{3})_", item.name)
        if match:
            item.user_properties.append(
                ("case_id", f"CCP-M2-{match[1].upper()}-{match[2]}")
            )


def _load_module(config, module, sys_path):
    path = source_path(config, module)
    spec = importlib.util.spec_from_file_location(f"ccp_m2_{module}", path)
    if spec is None or spec.loader is None:
        raise pytest.UsageError(f"无法加载源码：{path}")
    module_obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module_obj)
    return module_obj


@pytest.fixture(scope="session")
def halstead_metrics(pytestconfig):
    import sys
    directory = source_directory(pytestconfig)
    sys.path.insert(0, str(directory / IMPORT_ROOT))
    module = _load_module(pytestconfig, "halstead_parser", sys.path)
    return module.HalsteadMetrics()


@pytest.fixture(scope="session")
def extract_metrics(pytestconfig):
    import sys
    directory = source_directory(pytestconfig)
    sys.path.insert(0, str(directory / IMPORT_ROOT))
    module = _load_module(pytestconfig, "extract_metrics", sys.path)
    return module


@pytest.fixture
def write_cpp(tmp_path):
    def make(name, content):
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        return str(p)
    return make
