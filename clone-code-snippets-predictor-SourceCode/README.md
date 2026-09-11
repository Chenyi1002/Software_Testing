# Clone Code Snippets Predictor

面向 C/C++ 克隆代码片段的度量提取与缺陷预测数据准备工具。

本项目围绕 Apollo、Autoware 等项目的克隆检测结果和 Git 提交历史，提取克隆片段位置、代码度量及历史修改信息，生成包含启发式缺陷标签的数据表，并提供数据汇总与 PCA 特征分析脚本。

当前仓库主要包含研究用数据处理脚本及已有数据，尚未包含完整的缺陷分类模型训练、推理服务和统一流水线入口。

项目地址：[Chenyi1002/clone-code-snippets-predictor](https://github.com/Chenyi1002/clone-code-snippets-predictor)

## 1. 主要功能

| 功能 | 说明 | 对应脚本 |
| --- | --- | --- |
| 克隆片段提取 | 读取 Simian XML，按文件合并有交集的代码段，计算片段行数 | `Extract_CloneCode_Snippets.py` |
| Git 提交提取 | 按时间范围遍历提交，导出作者、文件路径、增删行数和 diff | `Extract_Commit.py` |
| 历史信息与标签 | 解析提交 XML，统计文件修改信息，依据修复关键词和区间交集生成标签 | `Extract_HistoryMetrics&Label.py` |
| 片段代码度量 | 读取指定行范围内的源代码，统计操作符和操作数 | `Extract_HalsteadMetrics.py` |
| 数据汇总 | 合并多个工作表中的代码区间并汇总度量、标签 | `Combine.py` |
| 特征分析 | 填充缺失值、执行 PCA、导出特征权重并绘图 | `PCA.py` |
| 独立代码分析 | 分析单个代码片段，或遍历目录批量分析 C/C++ 文件 | `Halstead_parser_code/` |

## 2. 目录结构

```text
clone-code-snippets-predictor/
├── README.md
├── Extract_CloneCode_Snippets.py
├── Extract_Commit.py
├── Extract_HistoryMetrics&Label.py
├── Extract_HalsteadMetrics.py
├── Combine.py
├── PCA.py
├── Halstead_parser_code/
│   ├── code_halstead_extract.py       # 片段级分析器
│   ├── project_halstead_extract.py    # 项目目录批量分析器
│   └── example.cpp                   # 示例源文件
├── clone_xml/
│   ├── apollo/                       # 各版本克隆检测 XML
│   └── autoware/
├── all_commit/
│   ├── apollo/                       # 各版本区间提交 XML
│   └── autoware/
└── results/
    ├── apollo.xlsx
    ├── apollo_aggregated.xlsx
    ├── autoware.xlsx
    ├── autoware_aggregated.xlsx
    └── feature_weights.csv
```

仓库中的 XML 数据体积较大。理解模块或进行局部开发时，可以只准备少量对应格式的数据；提取 Halstead 度量时，还需要本地存在对应版本的被分析源文件。

## 3. 环境准备

使用 Python 3。原始仓库没有锁定 Python 和第三方包版本，完成环境验证后应记录实际使用的版本。

| 依赖 | 用途 |
| --- | --- |
| `pandas`、`openpyxl` | 数据处理及 Excel 读写 |
| `pydriller`、Git | Git 提交历史提取 |
| `numpy`、`scikit-learn`、`matplotlib` | PCA 与可视化 |

XML、正则表达式和计数器等功能使用 Python 标准库。若只运行 `code_halstead_extract.py`，无需安装上述第三方 Python 包。使用已有克隆 XML 时无需运行 Simian；重新生成克隆检测结果时，需要另行准备该工具。

下面以 Windows PowerShell 为例。先获取仓库并进入项目根目录：

```powershell
git clone https://github.com/Chenyi1002/clone-code-snippets-predictor.git
cd clone-code-snippets-predictor
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pandas openpyxl pydriller numpy scikit-learn matplotlib
```

后续命令直接使用虚拟环境中的 Python，无需激活环境。原始仓库暂未提供 `requirements.txt`，因此当前采用显式安装依赖的方式。

## 4. 最小功能演示

若只想了解代码度量功能，可运行自带示例，无需准备完整 XML 数据和 Apollo/Autoware 源码：

```powershell
.\.venv\Scripts\python.exe -c "from Halstead_parser_code.code_halstead_extract import HalsteadMetrics; print(HalsteadMetrics().analyze('Halstead_parser_code/example.cpp'))"
```

分析成功时返回字典，包含操作符、操作数的种类数和出现次数，以及词汇量、长度和明细计数；处理失败时当前实现会打印错误并返回 `None`。

这是一条功能演示命令，不是自动化测试，也不代表完整流程已验证通过。

## 5. 数据处理流程

```text
克隆检测 XML ──→ 克隆片段位置 ───────────────┐
                                           │
Git 仓库 ──→ 提交 XML ──→ 历史统计与标签 ──┼──→ 片段数据表
                                           │        │
对应版本源文件 ──→ 操作符与操作数度量 ─────┘        ↓
                                                  汇总数据
                                                     ↓
                                               PCA 特征分析
```

各脚本需要分别执行。开始前请准备工作数据副本，确认输出目录已经存在，并关闭正在被 Excel 占用的工作簿。部分步骤会直接修改输入工作簿或覆盖同名结果文件。

### 5.1 提取克隆片段

```powershell
.\.venv\Scripts\python.exe Extract_CloneCode_Snippets.py
```

按提示输入克隆 XML 目录和目标 Excel 路径，例如 `clone_xml/apollo`、`results/apollo_work.xlsx`。

输入文件采用 `<项目名>-<版本号>-dup.xml` 命名，例如 `apollo-1.0.0-dup.xml`。解析器读取 `set` 下的 `block` 节点，使用 `sourceFile`、`startLineNumber`、`endLineNumber` 属性生成片段记录。

运行前及运行后需注意：

- 当前入口固定生成 `apollo-<版本号>` 前缀；处理 Autoware 等其他项目时，需要先调整此前缀逻辑。
- 当前解析器会把 `.cpp` 文件名转换为 `.cc`，后续路径匹配需采用一致规则。
- 写入函数会拼接原有记录与新记录，再替换工作表。重复运行可能产生重复数据，应使用新的工作文件或明确的重建流程。
- 创建新工作簿时可能保留默认空白工作表；后续遍历所有工作表前，应确认只保留有效的数据表。

### 5.2 准备提交历史

已有适用的 `all_commit/` 数据时，可以跳过重新提取。需要从 Git 仓库生成时，先修改 `Extract_Commit.py` 末尾的 `time_ranges` 和输出文件命名，再执行：

```powershell
.\.venv\Scripts\python.exe Extract_Commit.py
```

按提示输入被分析仓库的本地路径或远程地址。应准备目标时间范围所需的提交历史。

当前入口的时间范围固定为 2019-01-08 至 2019-06-28，输出名采用 `apollo_<开始日期>_<结束日期>_commit.xml`。下一步则依据文件名生成工作表名，因此需要把输出名、版本范围和已有工作表对应起来，不能直接假定两个脚本的默认值已经衔接。

### 5.3 提取历史信息与标签

首先检查 `Extract_HistoryMetrics&Label.py` 中 `update_excel()` 和 `lable()` 的 `prefix`。当前使用的路径模板为：

```text
D:\download\<工作表名>\<工作表名>\
```

调整路径映射，使拼接后的文件名与 Excel 的 `File` 列一致，再执行：

```powershell
.\.venv\Scripts\python.exe "Extract_HistoryMetrics&Label.py"
```

按提示输入提交 XML 目录及第一步生成的工作簿路径，例如 `all_commit/apollo`、`results/apollo_work.xlsx`。脚本名含有 `&`，运行时需保留引号。

当前文件命名规则为 `<项目名>_<起始版本>_<结束版本>_commit.xml`，对应工作表 `<项目名>-<起始版本>`。例如 `apollo_1.0.0_1.5.0_commit.xml` 对应 `apollo-1.0.0`。

程序按提交信息中的 `bug`、`fix`、`wrong`、`error`、`fail`、`problem`、`patch`、`correct` 等关键词识别疑似修复提交，再结合代码行范围生成 `Bug` 标签。这是启发式标签，不能将其直接视为人工确认的真实缺陷；`Bug=0` 也不能证明代码没有缺陷。

### 5.4 提取片段代码度量

先修改 `Extract_HalsteadMetrics.py` 中的 `excel_path`，使其指向前面的工作数据副本。确认 `File` 列中的源文件存在，且版本与片段行号对应，再执行：

```powershell
.\.venv\Scripts\python.exe Extract_HalsteadMetrics.py
```

当前默认路径为 `results\apollo.xlsx`。脚本依赖前三列中的 `File`、`cc_start_line`、`cc_end_line`，读取指定行范围并写回四项操作符、操作数指标。

如果 `.cc` 文件不存在，会尝试对应 `.cpp` 路径；仍找不到时，当前实现会删除该片段记录并保存结果。因此，运行前必须核对路径并保留输入副本。

### 5.5 汇总数据

当工作簿已包含片段位置、历史信息、代码度量和 `Bug` 列后，执行：

```powershell
.\.venv\Scripts\python.exe Combine.py
```

按提示输入工作簿路径和新的汇总结果路径，例如 `results/apollo_work.xlsx`、`results/apollo_work_aggregated.xlsx`。

当前实现读取所有工作表，将 `File` 按反斜杠分割后取最后一段作为分组键，合并重叠区间，对选中记录的度量求均值，对 `Bug` 取最大值。不同目录的同名文件可能进入同一组，使用结果前需确认这种分组方式符合分析目标。

### 5.6 PCA 特征分析（可选）

**此步骤需要先整理输入，原始汇总表不能直接假定可用。**

`PCA.py` 当前把最后一列作为标签，其余所有列作为特征。如果输入中仍包含字符串类型的 `File` 列，就不符合 PCA 的数值输入要求。运行前需要明确数值特征列、排除路径等标识字段，并确保标签不进入特征矩阵；可调整特征选择逻辑，或另存一份仅含选定数值特征和末列标签的数据表。

然后修改脚本中的 `file_path` 及输出位置，再执行：

```powershell
.\.venv\Scripts\python.exe PCA.py
```

当前实现以常数 0 填充缺失值，对各主成分载荷的绝对值取平均，输出特征权重 CSV 并显示柱状图。它没有进行标准化，也没有按解释方差加权；该权重反映的是当前计算规则，不等同于分类预测能力或因果重要性。

## 6. 主要数据字段

| 字段 | 含义与当前实现 |
| --- | --- |
| `File` | 文件路径；汇总后为按反斜杠截取的文件名 |
| `cc_start_line`、`cc_end_line` | 克隆片段起止行号，片段解析使用包含两端的区间 |
| `cc_lines` | 提取时为终止行减起始行加 1；汇总时对选中记录求均值 |
| `author_count` | 当前处理范围内成功解析记录的不同作者名数量 |
| `modify_count` | 当前处理范围内成功解析的文件修改记录数 |
| `avg_added`、`avg_deleted` | 文件修改记录的平均新增、删除行数；历史提取阶段取整 |
| `unique_operators`、`unique_operands` | 操作符、操作数的种类数 |
| `total_operators`、`total_operands` | 操作符、操作数的出现总次数 |
| `Bug` | 依据提交关键词和区间匹配生成的启发式二值标签 |

历史统计当前按文件计算，再写入该文件对应的片段行，不能将这些字段解释为已经精确计算的片段级修改次数。两个 Halstead 分析器的统计口径也不完全一致，片段流水线使用的是 `code_halstead_extract.py`。

## 7. 当前限制与验证状态

- 当前代码是分散的研究脚本，部分路径、项目名和时间范围写在源码中；迁移环境前需要配置。
- C/C++ 代码分析使用正则表达式和自定义词法规则，未使用完整编译器语法分析，复杂语言结构的处理需要进一步验证。
- diff 提取、多次修复记录的标签累计以及合并区间后的记录筛选，仍需进一步验证；此处不将静态分析线索计为已复现缺陷。
- 当前部分异常仅打印日志，并不会统一返回失败状态。判断执行是否成功时，应同时检查日志、输出文件和数据内容。
- 所依据版本中未提供自动化测试目录、测试运行入口或覆盖率报告，本文不声明测试通过率和已修复缺陷数量。

## 8. 使用说明

原始 README 将本仓库定位为论文配套代码，供参考与学习。所依据版本未提供独立的 `LICENSE` 文件，本文不额外声明开源许可证或授权条款。研究使用时应注明实际代码、数据和相关工作的来源。
