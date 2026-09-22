"""模块二 Halstead 度量分析器测试（CCP-M2-HM-001 至 HM-021）。

预期值依据 C/C++ Halstead 度量的正确语义独立计算；源码缺陷导致的失败
登记为缺陷，不修改被测源码。
"""
import pytest


def analyze(metrics, path, start=None, end=None):
    return metrics.analyze(path, start, end)


# HM-001 空文件：所有计数为 0
def test_hm_001_empty_file(halstead_metrics, write_cpp):
    path = write_cpp("empty.cpp", "")
    r = analyze(halstead_metrics, path)
    assert r["unique_operators"] == 0
    assert r["unique_operands"] == 0
    assert r["total_operators"] == 0
    assert r["total_operands"] == 0


# HM-002 纯声明行：声明的名称是操作数，声明关键字不是操作符
def test_hm_002_declaration_only(halstead_metrics, write_cpp):
    path = write_cpp("decl.cpp", "int a;\n")
    r = analyze(halstead_metrics, path)
    assert r["unique_operators"] == 0
    assert r["unique_operands"] == 1
    assert r["operands"] == {"a": 1}


# HM-003 整数字面量不作为操作数
def test_hm_003_integer_literal_excluded(halstead_metrics, write_cpp):
    path = write_cpp("assign.cpp", "int a = 10;\n")
    r = analyze(halstead_metrics, path)
    assert r["unique_operators"] == 1
    assert r["unique_operands"] == 1
    assert r["operands"] == {"a": 1}
    assert r["operators"] == {"=": 1}


# HM-004 浮点字面量不作为操作数（缺陷：'3.14' 被计入）
def test_hm_004_float_literal_excluded(halstead_metrics, write_cpp):
    path = write_cpp("float.cpp", "double x = 3.14;\n")
    r = analyze(halstead_metrics, path)
    assert "3.14" not in r["operands"]


# HM-005 十六进制字面量整体排除（缺陷：'0x1F' 被拆出 'x1F' 操作数）
def test_hm_005_hex_literal_excluded(halstead_metrics, write_cpp):
    path = write_cpp("hex.cpp", "int x = 0x1F;\n")
    r = analyze(halstead_metrics, path)
    assert "x1F" not in r["operands"]


# HM-006 复合赋值长操作符优先匹配，不拆成单字符
def test_hm_006_long_operator_priority(halstead_metrics, write_cpp):
    path = write_cpp("longop.cpp", "a <<= 2;\nb += 3;\n")
    r = analyze(halstead_metrics, path)
    assert r["operators"]["<<="] == 1
    assert r["operators"]["+="] == 1
    assert "<" not in r["operators"]
    assert "<<" not in r["operators"]


# HM-007 字符串字面量不参与计数
def test_hm_007_string_literal_excluded(halstead_metrics, write_cpp):
    path = write_cpp("str.cpp", 'printf("Sum: %d", a);\n')
    r = analyze(halstead_metrics, path)
    assert "STRING_LITERAL" not in r["operands"]
    assert "Sum" not in r["operands"]


# HM-008 字符字面量不参与计数（缺陷：'CHAR_LITERAL' 被计入操作数）
def test_hm_008_char_literal_excluded(halstead_metrics, write_cpp):
    path = write_cpp("char.cpp", "char c = 'x';\n")
    r = analyze(halstead_metrics, path)
    assert "CHAR_LITERAL" not in r["operands"]


# HM-009 行注释内容不计入
def test_hm_009_line_comment_removed(halstead_metrics, write_cpp):
    path = write_cpp("comment.cpp", "// this is a comment\nint a = 1;\n")
    r = analyze(halstead_metrics, path)
    assert "this" not in r["operands"]
    assert "comment" not in r["operands"]
    assert r["operands"] == {"a": 1}


# HM-010 块注释内容不计入
def test_hm_010_block_comment_removed(halstead_metrics, write_cpp):
    path = write_cpp("block.cpp", "/* block\ncomment */\nint b = 2;\n")
    r = analyze(halstead_metrics, path)
    assert "block" not in r["operands"]
    assert r["operands"] == {"b": 1}


# HM-011 #include 行整体移除
def test_hm_011_include_removed(halstead_metrics, write_cpp):
    path = write_cpp("include.cpp",
                     '#include <iostream>\n#include "x.h"\nint main(){return 0;}\n')
    r = analyze(halstead_metrics, path)
    assert "iostream" not in r["operands"]
    assert "x" not in r["operands"]
    assert r["operands"] == {"main": 1}
    assert r["operators"] == {"return": 1}


# HM-012 单行宏定义行移除；使用点的宏名仍按操作数计入
def test_hm_012_single_line_macro_removed(halstead_metrics, write_cpp):
    path = write_cpp("macro.cpp", "#define MAX 100\nint x = MAX;\n")
    r = analyze(halstead_metrics, path)
    # 定义行的数字字面量不残留、定义行不产生操作符；使用点 MAX 计入操作数
    assert "100" not in r["operands"]
    assert r["operators"] == {"=": 1}
    assert r["operands"] == {"x": 1, "MAX": 1}


# HM-013 续行宏定义整体移除（缺陷：宏体残留下 a、b、+）
def test_hm_013_multiline_macro_removed(halstead_metrics, write_cpp):
    path = write_cpp("macromulti.cpp",
                     "#define ADD(a,b) \\\n    ((a)+(b))\nint x = 1;\n")
    r = analyze(halstead_metrics, path)
    assert "a" not in r["operands"]
    assert "b" not in r["operands"]
    assert "+" not in r["operators"]
    assert r["operands"] == {"x": 1}


# HM-014 HTML 转义实体还原（缺陷：&lt;、&gt; 未被还原，'lt'/'gt' 计入操作数）
def test_hm_014_html_escape_unescaped(halstead_metrics, write_cpp):
    path = write_cpp("html.cpp", "a &amp;&amp; b &lt; c &gt; d;\n")
    r = analyze(halstead_metrics, path)
    assert "lt" not in r["operands"]
    assert "gt" not in r["operands"]
    assert r["operators"]["&&"] == 1


# HM-015 控制流关键字计为操作符
def test_hm_015_control_keywords(halstead_metrics, write_cpp):
    path = write_cpp("control.cpp", "if (a) { return 1; } else { return 0; }\n")
    r = analyze(halstead_metrics, path)
    assert r["operators"]["if"] == 1
    assert r["operators"]["else"] == 1
    assert r["operators"]["return"] == 2


# HM-016 声明关键字作为整体忽略（缺陷：'double' 被拆成 'do' + 'uble'）
def test_hm_016_declaration_keyword_whole(halstead_metrics, write_cpp):
    path = write_cpp("declkw.cpp", "double x = 1;\n")
    r = analyze(halstead_metrics, path)
    assert "do" not in r["operators"]
    assert "uble" not in r["operands"]


# HM-017 行号闭区间切片（第 2 行到第 2 行只统计该行）
def test_hm_017_line_range_inclusive(halstead_metrics, write_cpp):
    path = write_cpp("range.cpp", "int a;\nint b;\nint c;\n")
    r = analyze(halstead_metrics, path, 2, 2)
    assert r["operands"] == {"b": 1}


# HM-018 行号越界：返回空计数而非报错
def test_hm_018_line_range_out_of_bounds(halstead_metrics, write_cpp):
    path = write_cpp("oob.cpp", "int a;\nint b;\n")
    r = analyze(halstead_metrics, path, 5, 8)
    assert r["unique_operands"] == 0
    assert r["total_operators"] == 0


# HM-019 未指定行号时分析整个文件
def test_hm_019_whole_file_without_lines(halstead_metrics, write_cpp):
    path = write_cpp("whole.cpp", "int a;\nint b;\n")
    r = analyze(halstead_metrics, path)
    assert r["unique_operands"] == 2


# HM-020 起始行号 0 是非法输入，不应静默处理整个文件（缺陷：实际处理整文件）
def test_hm_020_zero_start_line_boundary(halstead_metrics, write_cpp):
    path = write_cpp("zero.cpp", "int a;\nint b;\n")
    r = analyze(halstead_metrics, path, 0, 2)
    # 行号从 1 开始；0 不应被当作“未指定”并静默退回整文件。
    assert r["operands"] != {"a": 1, "b": 1}


# HM-021 文件不存在返回 None
def test_hm_021_missing_file_returns_none(halstead_metrics, tmp_path):
    r = analyze(halstead_metrics, str(tmp_path / "nope.cpp"))
    assert r is None
