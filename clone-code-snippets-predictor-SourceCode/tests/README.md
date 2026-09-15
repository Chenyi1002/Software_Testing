# 模块一测试运行说明

本目录按《模块一实验设计方案》实现 40 条 pytest 用例。测试及设计均为 AI 辅助编写，应如实保留来源；课程模块一的 AI 使用限制见课程要求。

| 文件 | 内容 | 用例数 |
| --- | --- | --- |
| `conftest.py` | 动态加载源码、临时数据、结果比较、用例编号记录 | 公共配置，不计用例 |
| `test_clone_extraction.py` | CCP-M1-CE-001 至 012 | 12 |
| `test_history_label.py` | CCP-M1-HL-001 至 016 | 16 |
| `test_combine.py` | CCP-M1-CO-001 至 012，最后一条是模块集成 | 12 |

每个测试函数对应一条正式用例。HL-015 在独立工作簿中检查两种记录顺序，仍计一条用例。JUnit XML 中的 `case_id` 属性保存正式编号。

## 在正式项目中运行

把整个 `tests` 目录放到被测仓库根目录，使它与三个源码文件同级。先在项目虚拟环境安装依赖：

```powershell
python -m pip install pytest pandas openpyxl
python -m pytest tests -v
```

测试默认加载：

- `Extract_CloneCode_Snippets.py`
- `Extract_HistoryMetrics&Label.py`
- `Combine.py`

历史模块按文件路径动态导入，无需把原文件名中的 `&` 改掉。为兼容本地阅读副本，也接受 `Extract_HistoryMetrics_Label.py`；两者同时存在时优先加载原始 `&` 文件名。

## 在当前课程工作目录运行

当前工作目录中的源码位于 `tmp/project-review`。请显式指定它，以免测试到其他版本：

```powershell
python -m pytest tests --source-dir tmp/project-review -v
```

也可以传入其他源码目录的绝对路径。源码缺失时会报错，不会静默跳过测试或搜索其他目录作为替代。每次运行的完整输出会显示源码目录及三个文件的 SHA256。

本次验证环境为 Windows、Python 3.12.14、pytest 9.1.1、pandas 3.0.1、openpyxl 3.1.5、numpy 2.3.5。其他环境可运行，但应记录各自实际版本。

本机验证使用了 Codex 自带 Python，以及 `tmp/pytest-deps` 中隔离安装的 pytest 依赖，并未安装到系统 Python。若要直接复用本机验证环境，可在当前目录执行：

```powershell
$env:PYTHONPATH = (Resolve-Path 'tmp/pytest-deps').Path
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
& 'C:\Users\86265\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 -m pytest tests --source-dir tmp/project-review -v
```

这些临时依赖和上述本机路径不是提交项目所必需的内容。其他成员按前面的普通虚拟环境方式安装即可。

## 保存结果

在已安装依赖的 Python 环境中，给每轮结果使用独立目录。例如，以下命令适用于源码已位于仓库根目录的情况：

```powershell
New-Item -ItemType Directory -Force test-results/run-01
python -m pytest tests -v --tb=short --junitxml=test-results/run-01/results.xml
```

当前工作目录运行时需加上 `--source-dir tmp/project-review`。日志中的通过数和失败数必须据实填写；不要把通过率和自动化比例混为一谈。

## 已验证的基线结果

被测对象为先前下载的 `e53ac3008e681c113b6123189caea1779933b121` 源码阅读副本；源码未修复。

| 模块 | 总数 | 通过 | 失败 |
| --- | --- | --- | --- |
| CE | 12 | 11 | 1 |
| HL | 16 | 13 | 3 |
| CO | 12 | 10 | 2 |
| 合计 | 40 | 34 | 6 |

没有跳过项或初始化错误，严格通过率为 85%。CO-012 小型集成场景通过。

| 失败用例 | 观察到的问题 |
| --- | --- |
| CE-012 | 写入函数声称首次创建工作簿，但文件仍不存在 |
| HL-007 | 区块从 10 开始共 3 行，返回终点 13，预期为 12 |
| HL-008 | 同一文件两个 diff 区块仅返回一个 |
| HL-015 | 两种修复记录顺序得到标签 0 和 1，预期均为 1 |
| CO-008、CO-009 | 内部或链条中间的记录未纳入正确汇总，标签实际为 0，预期为 1 |

这六条失败对应五类问题，两个 CO 用例不重复计为两个缺陷。尚未进行源码修复或修复验证，因此不能声明已经完成课程要求的缺陷闭环。

未使用 `xfail`、`skip` 或把错误输出当作预期值来掩盖问题。原代码存在上述问题时，pytest 返回非零退出码是正常的失败报告。

## 数据与测试边界

- 使用 `tmp_path` 创建 XML 和 Excel；既有项目数据及源码不改动。
- XML 用标准库生成，Excel 采用真实读写；被测算法没有被 Mock。
- 文件结果按行内容、字段、区间、标签和数值核对，不仅检查文件存在。
- 代码中的 Windows 源文件路径是字符串匹配键，不需要实际建立那些源码目录。
- 汇总保留设计方案中的文件名分组、`cc_lines` 求均值规则，不要求项目尚未承诺的去重或跨平台路径功能。
- diff 测试验证差异区块范围，不等于精确修改行定位；多区块统计的提交去重不由 HL-008 证明。
- CO-012 的 Halstead 指标为固定上游输入，未测试 Halstead 算法。
- 初次调试中的 CO-012 因测试传入 `Path` 对象而失败，随后改为原脚本使用的字符串路径。这属于测试适配问题，不计入项目缺陷。

正式基线输出位于 `test-results/baseline/`，包括 `results.xml`、`pytest-output.txt` 和记录环境、哈希及各用例结果的 `manifest.json`。初次调试记录单独放在 `test-results/development/`，不能与正式基线混用。
