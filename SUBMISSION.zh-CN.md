# figspec 项目说明（活动申报用）

> 本文件用于“开源软件生态建设”活动的项目提交说明，可按实际活动模板裁剪。

## 一、项目定位

**figspec：把科研插图当代码来管理。**

figspec 是一个面向科研人员的开源图表工具链：用一份声明式 YAML 描述插图，
一条命令编译成符合目标期刊规范的 PDF/SVG/PNG，并在构建时自动完成期刊合规
检查、色盲可访问性检查与数据溯源。

一句话概括：**LaTeX 之于排版，Make 之于构建，figspec 之于科研插图。**

- 语言：Python 3.10+
- 许可证：MIT
- 代码规模：约 4.5k 行源码 + 1k 行测试
- 测试：138 个自动化测试，覆盖颜色科学、解析、渲染、lint、溯源、CLI
- 依赖：matplotlib、numpy、PyYAML、click（无网络、无 GPU、无大模型依赖）

## 二、为什么值得做

科研插图目前普遍处于“手工时代”，由此产生四类高频问题：

1. **期刊规范碎片化**：每家期刊的栏宽、字号、DPI 都不同，作者往往在返修时
   才发现图被缩放到 3.5 英寸后 4 pt 的字根本看不清。
2. **不可复现**：重跑 notebook 得到“看起来一样”的图，但文件并不相同，无法
   证明论文里的图与代码、数据一致。
3. **可访问性缺失**：约 8% 的男性读者存在红绿色觉障碍，常见配色对他们不可读；
   灰度打印时同样失效。
4. **图与数据脱节**：半年后无人能确认某张子图由哪份 CSV、哪个 commit 生成。

这四点都不是“审美问题”，而是工程问题，可以被工具化解决。

## 三、核心功能与创新点

### 1. 声明式规格（Spec as Code）

一份 YAML 描述画布、坐标轴、数据系列、图例、注释与多子图布局；支持
`extends` 继承与 `${ENV}` 插值，可 diff、可评审、可由脚本批量生成。

### 2. 期刊预设体系

内置 Nature、Science、Cell、IEEE、ACM、Elsevier、Springer、PLOS 八套预设，
把栏宽、字号、最小线宽、DPI、首选格式、首选配色沉淀为数据文件；新增期刊只需
一个 YAML，不必改代码。

### 3. 合规与可访问性 lint（18 条规则）

- **排版**：最终尺寸下最小字号、最小线宽、图幅是否落在期刊栏网格、是否超高；
- **色彩**：WCAG 2.1 对比度、在 Machado(2009) 二色视觉模拟下用 CIEDE2000
  判断系列颜色是否坍缩、彩虹色图、颜色数量上限；
- **结构**：是否只有位图、DPI 是否达标、图例/坐标轴标签是否缺失、单点折线、
  类别轴是否拥挤；
- **数据完整性**：缺失值、重复图例、**截断的柱状图坐标轴**（DA003，直接对应
  科研诚信问题）。

报告支持 text / JSON / SARIF 2.1.0，可直接接入 GitHub code scanning 与 CI 闸门。

### 4. 逐字节可复现

PDF（去除 CreationDate）、SVG（固定 hashsalt、去 Date）、PNG、EPS（剥离
CreationDate）在同一环境下**逐字节一致**，并有测试守护。

### 5. 溯源清单与漂移检测

每次构建输出 `<name>.figspec.json`，记录规格哈希、每个数据文件的 SHA-256 与
字节数、输出哈希与 DPI、Python/figspec/matplotlib/numpy 版本、git commit 与
工作区是否 dirty、lint 摘要。`figspec verify` 重新计算全部哈希并报告漂移，
退出码可被 CI 使用。

### 6. 工程化与生态友好

CLI（9 个子命令）+ 类型化 Python API + 静态 HTML 图库生成 + MkDocs 文档站 +
GitHub Actions 三平台三版本矩阵 + issue/PR 模板 + pre-commit + Dependabot。

## 四、与现有方案的关系

| | figspec | 期刊样式包（SciencePlots 等） | Vega-Lite / ggplot | notebook + DVC |
|---|---|---|---|---|
| 声明式规格 | ✅ | ❌ | ✅ | ❌ |
| 期刊合规检查 | ✅ | ❌ | ❌ | ❌ |
| 色盲可分辨性审计 | ✅ | ❌ | ❌ | ❌ |
| 逐字节可复现 | ✅ | ❌ | 部分 | ❌ |
| 溯源清单 | ✅ | ❌ | ❌ | ✅（仅数据） |
| 投稿级 PDF/SVG | ✅ | ✅ | 部分 | ✅ |

figspec 不与 matplotlib 竞争，而是给它补上“schema + 默认值 + 构建系统 +
质量闸门”。

## 五、生态建设价值

1. **用户基数大**：任何需要投稿的科研人员都是潜在用户，不限于某个学科。
2. **贡献门槛低**：新增期刊预设=一个 YAML；新增规则=一个函数；新增图元=一个
   函数。天然适合作为“good first issue”培养新贡献者。
3. **可组合**：输出标准 PDF/SVG，可接入 LaTeX、Overleaf、Word、期刊投稿系统；
   SARIF 可接入 IDE 与代码扫描；Python API 可嵌入既有实验流水线。
4. **可教学**：lint 规则本身就是“科研绘图规范”的代码化，适合作为课程与实验室
   培训材料。
5. **可持续**：无外部服务依赖，维护成本低；数据驱动的预设体系便于社区共同维护。

## 六、路线图

- **v0.2**：LaTeX 表格导出（表与图同源）、violin/contour 图元、Jupyter cell magic；
- **v0.3**：可复用 GitHub Action、规则插件机制、图库主题；
- **v1.0**：API 稳定、期刊预设扩展至 15+、与主流实验管理工具互操作。

## 七、如何验证

```bash
pip install -e ".[dev]"
pytest -q                      # 138 passed
figspec gallery examples -o site   # 六张示例图与 HTML 图库
figspec render examples/06-multi-panel.yaml -o out --strict
figspec verify out/06-multi-panel.figspec.json
```

## 八、许可与治理

MIT 许可证；贡献指南、行为准则、安全策略、变更日志、引用信息齐备；提交历史
按“脚手架 → 核心模型 → 渲染 → 检查 → 溯源 → 文档 → 示例”分阶段组织，便于
评审阅读。
