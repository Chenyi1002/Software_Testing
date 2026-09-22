"""模块二 Extract_HalsteadMetrics.py 提取与写回测试（CCP-M2-EX-001 至 EX-005）。

预期值依据脚本声明的功能独立构造；工作簿不存在时的写入行为按
“应创建文件”的语义断言。
"""
import pandas as pd
import pytest


@pytest.fixture
def sample_workbook(tmp_path):
    """构造含 File/cc_start_line/cc_end_line 三列的工作簿。"""
    df = pd.DataFrame({
        "File": ["a.cc", "b.cc", "a.cc"],
        "cc_start_line": [2, 5, 10],
        "cc_end_line": [4, 8, 12],
    })
    path = tmp_path / "sample.xlsx"
    df.to_excel(path, sheet_name="apollo-1.0.0", index=False)
    return str(path), df


# EX-001 正常读取前三列，返回有序记录
def test_ex_001_read_source_file(extract_metrics, sample_workbook):
    path, _ = sample_workbook
    records = extract_metrics.Get_SourceFile(path, "apollo-1.0.0")
    assert records is not None
    assert len(records) == 3
    assert records[0]["File"] == "a.cc"
    assert records[0]["Start_Line"] == 2
    assert records[0]["End_Line"] == 4
    assert records[2]["Start_Line"] == 10


# EX-002 工作簿文件不存在时返回 None
def test_ex_002_missing_workbook(extract_metrics, tmp_path):
    r = extract_metrics.Get_SourceFile(str(tmp_path / "none.xlsx"), "apollo-1.0.0")
    assert r is None


# EX-003 工作表不存在时返回 None
def test_ex_003_missing_sheet(extract_metrics, sample_workbook):
    path, _ = sample_workbook
    r = extract_metrics.Get_SourceFile(path, "no-such-sheet")
    assert r is None


# EX-004 度量写回后可重新读取并核对四个度量列
def test_ex_004_save_metrics_and_verify(extract_metrics, sample_workbook, tmp_path):
    path, _ = sample_workbook
    df = pd.read_excel(path, sheet_name="apollo-1.0.0")
    for i in range(len(df)):
        df.at[i, "unique_operators"] = 1
        df.at[i, "unique_operands"] = 2
        df.at[i, "total_operators"] = 3
        df.at[i, "total_operands"] = 4
    extract_metrics.save_metrics_to_excel(path, "apollo-1.0.0", df)
    back = pd.read_excel(path, sheet_name="apollo-1.0.0")
    assert list(back["unique_operators"]) == [1, 1, 1]
    assert list(back["unique_operands"]) == [2, 2, 2]
    assert list(back["total_operators"]) == [3, 3, 3]
    assert list(back["total_operands"]) == [4, 4, 4]


# EX-005 工作簿不存在时保存应创建文件（缺陷：mode='a' 无法首次创建）
def test_ex_005_save_creates_missing_workbook(extract_metrics, tmp_path):
    target = str(tmp_path / "brand_new.xlsx")
    df = pd.DataFrame({"col": [1]})
    extract_metrics.save_metrics_to_excel(target, "apollo-1.0.0", df)
    import os
    assert os.path.exists(target)
