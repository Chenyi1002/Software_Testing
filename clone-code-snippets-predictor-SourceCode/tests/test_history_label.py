import pandas as pd


def test_hl_001_fix_keyword(history_module):
    """R-HL-01 等价类：符合规则包含bug修复关键词。"""
    assert history_module.check_bug_flag("fix parser bug") == 1


def test_hl_002_case_insensitive(history_module):
    """R-HL-01 等价类：验证字符串大小写。"""
    assert history_module.check_bug_flag("FIX parser BUG") == 1


def test_hl_003_without_keyword(history_module):
    """R-HL-01 等价类：不含bug修复信息。"""
    assert history_module.check_bug_flag("add documentation") == 0


def test_hl_004_empty_message(history_module):
    """R-HL-01 边界值：空字符串。"""
    assert history_module.check_bug_flag("") == 0


def test_hl_005_intersection_endpoint(history_module):
    """R-HL-02 边界值：相邻有公共行。"""
    assert history_module.check_intersection((3, 8), (8, 12)) is True


def test_hl_006_adjacent_no_intersection(history_module):
    """R-HL-02 边界值：相邻无公共行。"""
    assert history_module.check_intersection((3, 8), (9, 12)) is False


def test_hl_007_diff_closed_endpoint(history_module, make_commit):
    """R-HL-03 边界值：旧侧 10 起始共 3 行，最后一行为 12。"""
    commit = make_commit(files=[{
        "path": "a.cc", "added": 1, "deleted": 1,
        "diff": "@@ -10,3 +10,3 @@\n context_before\n-old\n+new\n context_after\n",
    }])
    assert history_module.extract_diff_info(commit) == [
        ("a.cc", "Alice", 1, 1, 10, 12, 1),
    ]


def test_hl_008_all_diff_hunks(history_module, make_commit):
    """R-HL-03 场景法：同文件两个区块均须提取。"""
    commit = make_commit(files=[{
        "path": "a.cc", "added": 2, "deleted": 2,
        "diff": (
            "@@ -10,3 +10,3 @@\n before\n-old_a\n+new_a\n after\n"
            "@@ -30,2 +30,2 @@\n-old_b\n+new_b\n tail\n"
        ),
    }])
    actual = history_module.extract_diff_info(commit)
    assert len(actual) == 2, "同文件的第二个 diff 区块被遗漏"
    assert sorted(actual, key=lambda row: row[4]) == [
        ("a.cc", "Alice", 2, 2, 10, 12, 1),
        ("a.cc", "Alice", 2, 2, 30, 31, 1),
    ]
    # 这里验证区块提取，不把重复携带的文件增删总数累加成提交统计。


def test_hl_009_no_modified_files(history_module, make_commit):
    """R-HL-03 等价类：没有文件修改节点。"""
    assert history_module.extract_diff_info(make_commit(files=None)) == []


def test_hl_010_empty_statistics(history_module):
    """R-HL-04 等价类：没有解析记录。"""
    assert history_module.process_diff_lines([]) == ([], [])


def test_hl_011_repeated_author_and_integer_average(history_module):
    """R-HL-04 场景法：作者去重，平均增删向零取整。"""
    records = [
        ("a.cc", "Alice", 3, 1, 1, 3, 0),
        ("a.cc", "Alice", 4, 2, 8, 10, 1),
    ]
    assert history_module.process_diff_lines(records) == (
        [("a.cc", 1, 2, 3, 1)], [("a.cc", 8, 10, 1)],
    )


def test_hl_012_statistics_isolate_files(history_module):
    """R-HL-04 场景法：不同文件与作者独立统计，修复记录按标志筛选。"""
    records = [
        ("a.cc", "Alice", 2, 2, 1, 3, 1),
        ("b.cc", "Carol", 10, 4, 20, 22, 0),
        ("a.cc", "Bob", 6, 0, 8, 10, 0),
    ]
    stats, bugs = history_module.process_diff_lines(records)
    assert sorted(stats) == [("a.cc", 2, 2, 4, 1), ("b.cc", 1, 1, 10, 4)]
    assert bugs == [("a.cc", 1, 3, 1)]


def test_hl_013_add_columns_preserves_values(history_module):
    """R-HL-05 场景法：新列补零，已有列不清零。"""
    frame = pd.DataFrame({"File": ["a.cc", "b.cc"], "author_count": [7, 9]})
    actual = history_module.update_excel_columns(frame, ["author_count", "modify_count"])
    expected = pd.DataFrame({
        "File": ["a.cc", "b.cc"], "author_count": [7, 9], "modify_count": [0, 0],
    })
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, check_exact=True)


def test_hl_014_update_matched_rows_only(
    history_module, make_workbook, source_file_key, sheet_name,
):
    """R-HL-05 场景法：同文件多片段更新，其他文件和表保持不变。"""
    original = pd.DataFrame({
        "File": [source_file_key("a.cc"), source_file_key("a.cc"), source_file_key("b.cc")],
        "cc_start_line": [1, 10, 20], "cc_end_line": [5, 15, 25],
        "author_count": [0, 0, 9], "modify_count": [0, 0, 9],
        "avg_added": [0, 0, 9], "avg_deleted": [0, 0, 9],
    })
    control = pd.DataFrame({"note": ["不应改动"], "value": [77]})
    path = make_workbook({sheet_name: original, "control": control})
    history_module.update_excel(path, [("a.cc", 2, 3, 4, 1)], sheet_name)
    expected = original.copy(deep=True)
    expected.loc[[0, 1], ["author_count", "modify_count", "avg_added", "avg_deleted"]] = [2, 3, 4, 1]
    with pd.ExcelFile(path) as workbook:
        assert set(workbook.sheet_names) == {sheet_name, "control"}
        pd.testing.assert_frame_equal(workbook.parse(sheet_name), expected, check_dtype=False, check_exact=True)
        pd.testing.assert_frame_equal(workbook.parse("control"), control)


def test_hl_015_label_is_order_independent(
    history_module, make_workbook, source_file_key, sheet_name,
):
    """R-HL-06 场景法：已命中标签不能被清除，两种顺序合计一个用例。"""
    original = pd.DataFrame({
        "File": [source_file_key("a.cc")], "cc_start_line": [10], "cc_end_line": [20], "Bug": [0],
    })
    expected = original.copy(deep=True)
    expected["Bug"] = 1
    records = [("a.cc", 12, 14, 1), ("a.cc", 30, 32, 1)]
    results = []
    for index, order in enumerate((records, list(reversed(records)))):
        path = make_workbook({sheet_name: original}, filename=f"order_{index}.xlsx")
        history_module.lable(path, order, sheet_name)
        results.append(pd.read_excel(path, sheet_name=sheet_name))
    labels = [frame["Bug"].tolist() for frame in results]
    assert labels == [[1], [1]], f"两种顺序的标签为 {labels}，应均为 [[1], [1]]"
    for result in results:
        pd.testing.assert_frame_equal(result, expected, check_dtype=False, check_exact=True)


def test_hl_016_no_overlap_keeps_zero(
    history_module, make_workbook, source_file_key, sheet_name,
):
    """R-HL-06 等价类：全部修复区间均不相交。"""
    original = pd.DataFrame({
        "File": [source_file_key("a.cc")], "cc_start_line": [10], "cc_end_line": [20], "Bug": [0],
    })
    path = make_workbook({sheet_name: original})
    history_module.lable(path, [("a.cc", 1, 3, 1), ("a.cc", 30, 32, 1)], sheet_name)
    pd.testing.assert_frame_equal(
        pd.read_excel(path, sheet_name=sheet_name), original, check_dtype=False, check_exact=True,
    )
