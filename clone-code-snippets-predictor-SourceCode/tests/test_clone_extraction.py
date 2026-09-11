import xml.etree.ElementTree as ET

import pandas as pd
import pytest


def test_ce_001_empty_blocks(clone_module):
    """R-CE-01 等价类：空输入。"""
    assert clone_module.merge_blocks([]) == []


def test_ce_002_single_line(clone_module):
    """R-CE-01 边界值：仅一行代码。"""
    assert clone_module.merge_blocks([(7, 7)]) == [[7, 7]]


def test_ce_003_shared_endpoint(clone_module):
    """R-CE-01 边界值：有重复行。"""
    assert clone_module.merge_blocks([(1, 5), (5, 9)]) == [[1, 9]]


def test_ce_004_adjacent_blocks(clone_module):
    """R-CE-01 边界值：代码段相邻但不相交。"""
    assert clone_module.merge_blocks([(1, 5), (6, 9)]) == [[1, 5], [6, 9]]


def test_ce_005_unsorted_chain(clone_module):
    """R-CE-01 场景法：多片段有重叠。"""
    assert clone_module.merge_blocks([(8, 12), (1, 5), (4, 9)]) == [[1, 12]]


def test_ce_006_nested_and_duplicate(clone_module):
    """R-CE-01 等价类：包含和重复区间。"""
    assert clone_module.merge_blocks([(1, 10), (3, 4), (1, 10)]) == [[1, 10]]


def test_ce_007_xml_merge_and_extension(clone_module, make_clone_xml):
    """R-CE-02/03 场景法：同文件有重叠合并。"""
    path = make_clone_xml([("a.cpp", 2, 5), ("a.cpp", 4, 8)])
    assert clone_module.parse_simian_xml(path) == [
        {"File": "a.cc", "cc_start_line": 2, "cc_end_line": 8, "cc_lines": 7},
    ]


def test_ce_008_xml_distinct_files(clone_module, make_clone_xml):
    """R-CE-02 等价类：相同区间不同文件不能合并。"""
    path = make_clone_xml([("b.cc", 2, 5), ("a.cc", 2, 5)])
    actual = sorted(clone_module.parse_simian_xml(path), key=lambda row: row["File"])
    assert actual == [
        {"File": "a.cc", "cc_start_line": 2, "cc_end_line": 5, "cc_lines": 4},
        {"File": "b.cc", "cc_start_line": 2, "cc_end_line": 5, "cc_lines": 4},
    ]


def test_ce_009_xml_without_blocks(clone_module, make_clone_xml):
    """R-CE-03 等价类：合法但无克隆块。"""
    assert clone_module.parse_simian_xml(make_clone_xml([])) == []


def test_ce_010_malformed_xml(clone_module, tmp_path):
    """R-CE-03 等价类：损坏 XML 应报告解析错误。"""
    path = tmp_path / "broken.xml"
    path.write_text("<simian><set>", encoding="utf-8")
    with pytest.raises(ET.ParseError):
        clone_module.parse_simian_xml(path)


def test_ce_011_add_sheet_preserves_control(
    clone_module, make_workbook, sheet_name, assert_result_table,
):
    """R-CE-04 场景法：增加目标表，其他表保持不变。"""
    control = pd.DataFrame({"note": ["保留内容"], "value": [99]})
    path = make_workbook({"control": control})
    records = [{"File": "a.cc", "cc_start_line": 2, "cc_end_line": 5, "cc_lines": 4}]
    clone_module.update_excel_with_clone_counts(path, sheet_name, records)
    with pd.ExcelFile(path) as workbook:
        assert set(workbook.sheet_names) == {"control", sheet_name}
        assert_result_table(workbook.parse(sheet_name), records)
        pd.testing.assert_frame_equal(workbook.parse("control"), control)


def test_ce_012_create_missing_workbook(clone_module, tmp_path, sheet_name, assert_result_table):
    """R-CE-04 场景法：按函数文档验证首次创建，不能预先帮它创建文件。"""
    path = tmp_path / "new.xlsx"
    records = [{"File": "a.cc", "cc_start_line": 2, "cc_end_line": 5, "cc_lines": 4}]
    assert not path.exists()
    clone_module.update_excel_with_clone_counts(path, sheet_name, records)
    assert path.is_file(), "函数文档声明会创建工作簿，但调用后文件不存在"
    assert_result_table(pd.read_excel(path, sheet_name=sheet_name), records)
