# 模块二测试运行说明

本目录按《模块二实验设计方案》实现 26 条 pytest 用例，采用方案2（测试手段含 AI）：被测对象为 Halstead 度量提取模块，测试用例设计与脚本由 AI 辅助生成，人工修正预期值后执行。

| 文件 | 内容 | 用例数 |
| --- | --- | --- |
| `conftest.py` | 动态加载源码、临时数据、用例编号记录 | 公共配置，不计用例 |
| `test_halstead_metrics.py` | CCP-M2-HM-001 至 HM-021（Halstead 度量分析器） | 21 |
| `test_extract_metrics.py` | CCP-M2-EX-001 至 EX-005（度量提取与写回） | 5 |

每个测试函数对应一条正式用例，JUnit XML 中的 `case_id` 属性保存正式编号。

## 运行方式

把整个 `Test_Module2` 目录放到被测仓库根目录同级，在已安装依赖的环境中执行：

```bash
python3 -m pip install pytest pandas openpyxl numpy
python3 -m pytest Test_Module2/tests -v --tb=short --junitxml=Test_Module2/test-results/run-01/results.xml
```

测试默认加载：

- `SourceCode/Halstead_parser_code/code_halstead_extract.py`
- `SourceCode/Extract_HalsteadMetrics.py`

## 已验证的基线结果

被测对象为版本 `e53ac30` 的源码阅读副本；源码未修复。运行环境：macOS，Python 3.14.7，pytest 9.1.1，pandas、openpyxl、numpy 已安装。

| 组 | 总数 | 通过 | 失败 |
| --- | --- | --- | --- |
| HM | 21 | 13 | 8 |
| EX | 5 | 5 | 0 |
| 合计 | 26 | 18 | 8 |

严格通过率 69.23%。8 条失败对应 7 个缺陷（HM-004 与 HM-016 在同一段 `double x = 3.14;` 上暴露两个独立根因，分计）。

| 失败用例 | 观察到的问题 |
| --- | --- |
| HM-004 | 浮点字面量 `3.14` 被计入操作数 |
| HM-005 | 十六进制字面量 `0x1F` 被拆出 `x1F` 操作数 |
| HM-008 | 字符字面量替换标记 `CHAR_LITERAL` 被计入操作数 |
| HM-013 | 续行宏只移除第一行，宏体 `((a)+(b))` 残留 |
| HM-014 | HTML 实体 `&lt;`、`&gt;` 未还原，`lt`、`gt` 被计入操作数 |
| HM-016 | 声明关键字 `double` 被拆成操作符 `do` 与操作数 `uble` |
| HM-020 | 起始行号 0 被静默当作“未指定”，处理整个文件 |
| EX-005 | 工作簿不存在时 `save_metrics_to_excel` 以追加模式打开失败，文件未创建 |

尚未进行源码修复或修复验证，不能声明已经完成缺陷闭环。测试数据与源码均不改动，未使用 xfail、skip 或把错误输出当作预期值来掩盖问题。

## AI 辅助说明

- AI 初稿生成 26 条用例设计；人工审查时发现并修正 AI 预期值错误 1 处（单行宏使用点的宏名 `MAX` 应计入操作数，AI 初稿误以为宏名应整体排除）。
- 基线 8 条失败由 AI 初稿未覆盖、人工补充的边界用例暴露（浮点/十六进制字面量、字符字面量、HTML 实体、续行宏、行号 0、新建工作簿等）。
- 详细过程与差异对比见《模块二测试报告》。
