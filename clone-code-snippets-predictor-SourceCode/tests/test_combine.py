import pandas as pd


def test_co_001_empty_intervals(combine_module):
    """R-CO-01 等价类：空输入。"""
    assert combine_module.merge_intervals([]) == []


def test_co_002_single_line(combine_module):
    """R-CO-01 边界值：一行区间。"""
    assert combine_module.merge_intervals([(4, 4)]) == [(4, 4)]


def test_co_003_shared_endpoint(combine_module):
    """R-CO-01 边界值：公共端点。"""
    assert combine_module.merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]


def test_co_004_adjacent_intervals(combine_module):
    """R-CO-01 边界值：相邻不合并。"""
    assert combine_module.merge_intervals([(1, 3), (4, 6)]) == [(1, 3), (4, 6)]


def test_co_005_unsorted_chain(combine_module):
    """R-CO-01 场景法：无序链式重叠。"""
    assert combine_module.merge_intervals([(8, 12), (1, 5), (4, 9)]) == [(1, 12)]


def test_co_006_nested_and_duplicate(combine_module):
    """R-CO-01 等价类：包含和重复。"""
    assert combine_module.merge_intervals([(1, 10), (3, 4), (1, 10)]) == [(1, 10)]


def test_co_007_merge_across_sheets(
    combine_module, make_workbook, metric_row, tmp_path, assert_result_table,
):
    """R-CO-02/03 场景法：跨表合并，平均值与最大标签。"""
    path = make_workbook({
        "v1": [metric_row(r"D:\snapshot1\a.cc", 1, 5, value=2, bug=0)],
        "v2": [metric_row(r"D:\snapshot2\a.cc", 4, 8, value=4, bug=1)],
    })
    output = tmp_path / "aggregated.xlsx"
    combine_module.merge_and_aggregate_data(path, output)
    expected = metric_row("a.cc", 1, 8, value=3, bug=1, cc_lines=5)
    assert_result_table(pd.read_excel(output), [expected])


def test_co_008_include_contained_record(
    combine_module, make_workbook, metric_row, tmp_path, assert_result_table,
):
    """R-CO-03 场景法：内部记录必须参与标签与均值。"""
    path = make_workbook({"v1": [
        metric_row(r"D:\source\a.cc", 1, 20, value=2, bug=0),
        metric_row(r"D:\source\a.cc", 5, 10, value=8, bug=1),
    ]})
    output = tmp_path / "aggregated.xlsx"
    combine_module.merge_and_aggregate_data(path, output)
    expected = metric_row("a.cc", 1, 20, value=5, bug=1, cc_lines=13)
    assert_result_table(pd.read_excel(output), [expected])


def test_co_009_include_middle_of_chain(
    combine_module, make_workbook, metric_row, tmp_path, assert_result_table,
):
    """R-CO-03 场景法：链条中间记录也参与汇总。"""
    path = make_workbook({"v1": [
        metric_row(r"D:\source\a.cc", 1, 5, value=2, bug=0),
        metric_row(r"D:\source\a.cc", 4, 9, value=8, bug=1),
        metric_row(r"D:\source\a.cc", 8, 12, value=2, bug=0),
    ]})
    output = tmp_path / "aggregated.xlsx"
    combine_module.merge_and_aggregate_data(path, output)
    expected = metric_row("a.cc", 1, 12, value=4, bug=1, cc_lines=16 / 3)
    assert_result_table(pd.read_excel(output), [expected])


def test_co_010_distinct_files(
    combine_module, make_workbook, metric_row, tmp_path, assert_result_table,
):
    """R-CO-02/03 等价类：不同文件同区间不相互影响。"""
    path = make_workbook({"v1": [
        metric_row(r"D:\source\b.cc", 1, 5, value=8, bug=1),
        metric_row(r"D:\source\a.cc", 1, 5, value=2, bug=0),
    ]})
    output = tmp_path / "aggregated.xlsx"
    combine_module.merge_and_aggregate_data(path, output)
    assert_result_table(pd.read_excel(output), [
        metric_row("a.cc", 1, 5, value=2, bug=0),
        metric_row("b.cc", 1, 5, value=8, bug=1),
    ])


def test_co_011_disjoint_and_input_unchanged(
    combine_module, make_workbook, metric_row, tmp_path, assert_result_table,
):
    """R-CO-02/04 场景法：不相交结果分开保存，原工作簿保持不变。"""
    path = make_workbook({
        "v1": [metric_row(r"D:\source\a.cc", 1, 3, value=2, bug=0)],
        "v2": [metric_row(r"D:\source\a.cc", 8, 10, value=8, bug=1)],
    })
    before = pd.read_excel(path, sheet_name=None)
    before_bytes = path.read_bytes()
    output = tmp_path / "aggregated.xlsx"
    combine_module.merge_and_aggregate_data(path, output)
    assert_result_table(pd.read_excel(output), [
        metric_row("a.cc", 1, 3, value=2, bug=0),
        metric_row("a.cc", 8, 10, value=8, bug=1),
    ])
    assert path.read_bytes() == before_bytes, "输入工作簿被改写"
    after = pd.read_excel(path, sheet_name=None)
    assert before.keys() == after.keys()
    for name in before:
        pd.testing.assert_frame_equal(after[name], before[name])


def test_co_012_small_pipeline(
    clone_module, history_module, combine_module,
    make_clone_xml, make_commit, write_commit_xml, make_workbook,
    source_file_key, sheet_name, tmp_path, assert_result_table,
):
    """综合需求 场景法：三个模块的真实 XML/Excel 数据传递。"""
    a_key, b_key = source_file_key("a.cc"), source_file_key("b.cc")
    xml_path = make_clone_xml([(a_key, 1, 3), (a_key, 3, 5), (b_key, 10, 12)])
    clone_records = clone_module.parse_simian_xml(xml_path)
    expected_clones = [
        {"File": a_key, "cc_start_line": 1, "cc_end_line": 5, "cc_lines": 5},
        {"File": b_key, "cc_start_line": 10, "cc_end_line": 12, "cc_lines": 3},
    ]
    assert_result_table(pd.DataFrame(clone_records), expected_clones)
    # 本场景提供已存在的空目标表，首次创建由 CE-012 独立验证。
    workbook = make_workbook({sheet_name: pd.DataFrame(columns=list(expected_clones[0]))})
    clone_module.update_excel_with_clone_counts(workbook, sheet_name, clone_records)
    assert_result_table(pd.read_excel(workbook, sheet_name=sheet_name), expected_clones)

    commit = make_commit(files=[{
        "path": "a.cc", "added": 1, "deleted": 1,
        "diff": "@@ -2,2 +2,2 @@\n-old\n+new\n context\n",
    }])
    commits_path = write_commit_xml([commit])
    # 原脚本使用字符串路径调用 minidom，不要求它额外支持 pathlib.Path。
    stats, bugs = history_module.extract_diff_lines(str(commits_path))
    assert stats == [("a.cc", 1, 1, 1, 1)]
    # 区块端点由 HL-007 精确验证；此场景检查最终业务数据。
    history_module.update_excel(workbook, stats, sheet_name)
    history_module.lable(workbook, bugs, sheet_name)
    labelled = pd.read_excel(workbook, sheet_name=sheet_name)
    expected_labelled = [
        {**expected_clones[0], "author_count": 1, "modify_count": 1,
         "avg_added": 1, "avg_deleted": 1, "Bug": 1},
        {**expected_clones[1], "author_count": 0, "modify_count": 0,
         "avg_added": 0, "avg_deleted": 0, "Bug": 0},
    ]
    assert_result_table(labelled, expected_labelled)

    # 固定上游度量输入，不执行也不模拟 Halstead 分析算法。
    fixed_metrics = {"unique_operators": 1, "unique_operands": 2,
                     "total_operators": 3, "total_operands": 4}
    for column, value in fixed_metrics.items():
        labelled[column] = value
    with pd.ExcelWriter(workbook, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        labelled.to_excel(writer, sheet_name=sheet_name, index=False)
    output = tmp_path / "pipeline_result.xlsx"
    combine_module.merge_and_aggregate_data(workbook, output)
    expected = [
        {**expected_labelled[0], **fixed_metrics, "File": "a.cc"},
        {**expected_labelled[1], **fixed_metrics, "File": "b.cc"},
    ]
    assert_result_table(pd.read_excel(output), expected)
