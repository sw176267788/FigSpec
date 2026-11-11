<div align="center">

<img src="docs/assets/hero.png" alt="由 YAML 规格渲染出的六张投稿级科研图" width="780">

# figspec

**把图当代码来管：声明式、期刊合规、可复现的科研绘图工具链。**

[![CI](https://github.com/sw176267788/FigSpec/actions/workflows/ci.yml/badge.svg)](https://github.com/sw176267788/FigSpec/actions/workflows/ci.yml)
[![Docs](https://github.com/sw176267788/FigSpec/actions/workflows/docs.yml/badge.svg)](https://sw176267788.github.io/FigSpec/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776ab.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f.svg)](LICENSE)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](CHANGELOG.md)

[English](README.md) · [简体中文](README.zh-CN.md)

</div>

图是构建产物，但多数实验室仍把它当作“某个人手工调好的文件”。**figspec**
把一份很小的 YAML 编译成可直接投稿的图：它知道 Nature 单栏是 3.504 英寸、
5 pt 的字在最终尺寸下还能不能看清、哪两种颜色在红绿色盲眼里会糊成一片——这些
不必每投一篇论文就重学一遍。

```bash
figspec render figure.yaml -o figures     # → figures/figure.{pdf,svg,png}
figspec lint   figure.yaml --journal nature
figspec verify figures/figure.figspec.json
```

> **状态**：v0.1.0（alpha）。规格、渲染、lint、溯源清单与 CLI 均可用，138 个
> 测试覆盖核心路径；v1.0 之前公开 API 仍可能在小版本间调整。路线图见下文。

## 目录

- [为什么需要它](#为什么需要它)
- [特性](#特性)
- [安装](#安装)
- [快速开始](#快速开始)
- [规格格式](#规格格式)
- [期刊预设](#期刊预设)
- [合规检查](#合规检查)
- [可复现构建](#可复现构建)
- [CLI](#cli)
- [Python API](#python-api)
- [仓库结构](#仓库结构)
- [与同类工具的关系](#与同类工具的关系)
- [路线图](#路线图)
- [参与贡献](#参与贡献)
- [引用](#引用)
- [许可](#许可)

## 为什么需要它

如果你写过论文，下面四条大概都遇到过：

- **每家期刊要的数字都不同。** 栏宽、字号、线宽、DPI 藏在没人读的投稿指南里，
  直到返修才发现：5 英寸下好看的图，缩到 3.5 英寸后字只有 4 pt。
- **“同一张图”永远不是同一个文件。** 重跑一次 notebook、更新一次 matplotlib
  默认值，图看起来差不多，文件却完全不同，没人能证明 PDF 里是哪一版。
- **配色会悄悄失效。** 约 8% 的男性读者分不清红绿，浅色在打印或灰度下直接消失。
- **图和数据会脱节。** 半年后没人说得清子图 (c) 是哪份 CSV、哪个 commit 画的。

figspec 把这四条当作工程问题处理：一个 schema、一个编译器、一个 linter、
一份清单。

## 特性

- **声明式规格**：尺寸、坐标轴、数据系列、图例、注释、多子图布局写在一个
  YAML/JSON 里，可 diff、可评审、可由脚本生成。
- **8 套期刊预设**：Nature、Science、Cell、IEEE、ACM、Elsevier、Springer、PLOS，
  也可用 `--journal-file` 加载自定义预设。
- **18 条 lint 规则**：最终尺寸下的最小字号、线宽、WCAG 对比度、色盲可分辨性
  （在模拟二色视觉上计算 CIEDE2000）、DPI、图例与坐标轴标签、彩虹色图、截断的
  柱状图坐标轴。
- **逐字节可复现**：同一环境下 PDF/SVG/PNG/EPS 完全一致，时间戳与随机 id 被剥离。
- **溯源清单**：每次构建记录输入哈希、依赖版本、输出哈希与 git 状态；
  `figspec verify` 检测漂移。
- **多子图**：显式或自动网格、共享坐标轴、`(a)`–`(d)` 标号、逐面板图例。
- **可接入 CI**：`--strict`、`--fail-on`、JSON 与 SARIF 2.1.0 输出，把图的质量
  变成构建闸门。
- **库优先**：CLI 只是带类型的 Python API 的一层薄壳。

## 安装

figspec 尚未发布到 PyPI，请从仓库安装：

```bash
pip install "git+https://github.com/sw176267788/FigSpec.git"
```

或者克隆后开发：

```bash
git clone https://github.com/sw176267788/FigSpec.git
cd FigSpec
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

需要 **Python 3.10+** 与 matplotlib 3.7+；运行时依赖只有 matplotlib、numpy、
PyYAML、click。不需要 LaTeX、浏览器或网络。

## 快速开始

```bash
figspec init my-paper                     # 生成 figure.yaml 与 data/loss.csv
figspec render my-paper/figure.yaml -o figures
figspec lint   my-paper/figure.yaml --journal nature
```

`render` 会报告产物、lint 结果与清单位置：

```
  [ok] figure.pdf                23.1 KiB
  [ok] figure.svg                28.6 KiB
  [ok] figure.png               135.6 KiB
rendered 3 file(s) in 0.72s
lint: clean
provenance: figures/figure.figspec.json
```

## 规格格式

```yaml
version: 1

meta:
  title: 训练与验证损失
  tags: [deep-learning, training]

figure:
  journal: nature        # 栏宽、字体、DPI、最小字号都来自这里
  layout: single         # single | 1.5 | double | custom
  formats: [pdf, svg, png]

style:
  palette: okabe-ito     # 色盲友好，前五种颜色对比度均 ≥ 3:1
  grid: true

axes:
  x: {label: Epoch, limits: [0, 41]}
  y: {label: Cross-entropy loss}

series:
  - type: line
    data: data/loss.csv
    x: epoch
    y: [train, val]
    labels: [Train, Validation]
    marker: o
    markersize: 2.2
```

七种图元：`line`、`scatter`、`bar`、`box`、`errorbar`、`area`、`heatmap`。
数据可来自 CSV、TSV、JSON、`.npy`/`.npz`，也可以直接内联；规格之间可用
`extends` 继承，字符串支持 `${ENV}` 插值。

完整字段说明见 **[docs/spec-reference.md](docs/spec-reference.md)**。

## 期刊预设

| 预设 | 单栏 | 双栏 | 字号（最小） | 位图 DPI |
|---|---|---|---|---|
| `nature` | 3.504 in | 7.205 in | 7 (5) pt | 600 |
| `science` | 2.165 in | 7.244 in | 6 (5) pt | 300 |
| `cell` | 3.346 in | 6.850 in | 6 (5) pt | 300 |
| `ieee` | 3.500 in | 7.160 in | 8 (6) pt | 300 |
| `acm` | 3.330 in | 7.000 in | 8 (6) pt | 300 |
| `elsevier` | 3.543 in | 7.480 in | 8 (6) pt | 300 |
| `springer` | 3.307 in | 6.850 in | 8 (6) pt | 300 |
| `plos` | 3.270 in | 6.810 in | 8 (6) pt | 300 |

```bash
figspec journals          # 表格
figspec journals --json   # 机器可读，含来源链接
```

新增一套预设只需一个 YAML 文件，见 [docs/journals.md](docs/journals.md)。

## 合规检查

`figspec lint` 会先构建图，再检查真实图元并给出带稳定编号的结论。例如：

```
figure.yaml: 1 error(s), 1 warning(s), 0 note(s)
  ERROR   FS001 2 text elements render at 4.0 pt, below the 5.0 pt minimum
          hint: raise font_size, shorten tick labels, or drop the label 'validation split'
  WARNING DA003 panel 0 bars start at 50 instead of zero
          hint: set the y limit to 0, or switch the series to 'errorbar'
```

| 方向 | 编号 | 典型问题 |
|---|---|---|
| 排版 | `FS001`–`FS004` | 字号低于期刊下限、线过细、图幅偏离栏网格 |
| 色彩 | `CO001`–`CO004` | 对比度低于 3:1、二色视觉下颜色坍缩、彩虹色图 |
| 结构 | `ST001`–`ST007` | 只有位图、DPI 不足、缺图例或坐标轴标签 |
| 数据 | `DA001`–`DA003` | 缺失值、重复图例、截断的柱状图坐标轴 |

报告支持 text / JSON / SARIF 2.1.0；每条规则的动机见
[docs/lint-rules.md](docs/lint-rules.md)。

## 可复现构建

每次构建都会在产物旁写下 `<stem>.figspec.json`，记录规格哈希、每个输入文件的
SHA-256、输出哈希与 DPI、依赖版本以及 git 提交。之后用 `verify` 重新计算：

```
$ figspec verify figures/figure.figspec.json
verifying figures/figure.figspec.json
  OK   schema: figspec/provenance/v1
  OK   spec: figure.yaml matches
  OK   input loss.csv: loss.csv matches
  OK   output figure.pdf: figure.pdf matches
  OK   environment: tool versions match
```

同一环境下 PDF/SVG/PNG/EPS 的渲染结果是确定的，测试中通过逐字节比较断言。
matplotlib 升级带来的差异会出现在清单里，而不是悄悄发生。详见
[docs/provenance.md](docs/provenance.md)。

## CLI

```
figspec init [DIR]                 生成规格与示例数据
figspec render SPEC [-o DIR]       构建 PDF/SVG/PNG/EPS
figspec lint SPEC                  合规与可访问性检查
figspec verify MANIFEST            校验清单是否漂移
figspec gallery SOURCES [-o DIR]   渲染为静态 HTML 图库
figspec journals                   列出期刊预设
figspec palettes                   列出配色
figspec rules                      列出 lint 规则
figspec doctor                     环境自检
```

各命令的参数与退出码见 [docs/cli.md](docs/cli.md)。

## Python API

```python
import figspec

outcome = figspec.render("figure.yaml", "out/", journal="nature", strict=True)
print(outcome.report.to_text())
for output in outcome.outputs:
    print(output.path, output.sha256[:12])
outcome.close()
```

底层接口同样是公开的：`figspec.load_spec`、`figspec.render.build`、
`figspec.render.export`、`figspec.lint.lint_result`、
`figspec.provenance.create_manifest`。

## 仓库结构

```
src/figspec/
├── spec/          规格模型、校验、YAML/JSON 加载
├── data/          CSV/TSV/JSON/NPY 读取与序列准备
├── palette/       颜色科学、色盲模拟、配色
├── journals/      期刊预设 YAML 与加载器
├── render/        样式解析、多子图、图元、确定性导出
├── lint/          18 条规则与 text/JSON/SARIF 报告
├── provenance/    清单与漂移校验
├── api.py         render / lint / verify 便捷接口
└── cli.py         click 命令
tests/             138 个测试，约 9 秒
examples/          六张 lint-clean 的示例图及其数据
docs/              MkDocs 文档站（发布到 GitHub Pages）
scripts/           资源与示例数据生成脚本
```

更多设计说明见 [docs/architecture.md](docs/architecture.md)。

## 与同类工具的关系

| | figspec | 期刊样式包 | Vega-Lite / ggplot | notebook + DVC |
|---|---|---|---|---|
| 声明式规格 | ✅ | ❌ | ✅ | ❌ |
| 期刊合规检查 | ✅ | ❌ | ❌ | ❌ |
| 色盲可分辨性审计 | ✅ | ❌ | ❌ | ❌ |
| 逐字节可复现 | ✅ | ❌ | 部分 | ❌ |
| 溯源清单 | ✅ | ❌ | ❌ | ✅（仅数据） |
| 投稿级 PDF/SVG | ✅ | ✅ | 部分 | ✅ |

figspec 不替代 matplotlib，而是给它补上 schema、默认值与构建系统。它有意做得窄：
只产出论文插图，不做仪表盘。

## 路线图

- **v0.2**：LaTeX 表格导出、violin/contour 图元、Jupyter cell magic。
- **v0.3**：可复用的 GitHub Action、第三方规则与图元插件机制。
- **v1.0**：API 稳定、期刊预设扩展到 15+、与实验管理工具互操作。

想法与投票请走 [issue tracker](https://github.com/sw176267788/FigSpec/issues)。

## 参与贡献

欢迎贡献。最合适的第一份 PR 只碰一个文件加一个测试：

- **新增期刊预设** —— `src/figspec/journals/data/` 里一个 YAML；
- **新增 lint 规则** —— `src/figspec/lint/rules.py` 里一个带装饰器的函数；
- **新增图元** —— `src/figspec/render/plots.py` 里一个函数；
- **新增配方** —— `docs/recipes.md` 里一段可复制的配置。

先读 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [docs/contributing.md](docs/contributing.md)。
参与即表示同意遵守 [行为准则](CODE_OF_CONDUCT.md)。

## 引用

如果 figspec 对你的研究有帮助，请通过 [CITATION.cff](CITATION.cff) 引用：

```bibtex
@software{figspec2026,
  title     = {figspec: declarative, publication-ready, reproducible scientific figures},
  author    = {{The FigSpec Authors}},
  year      = {2026},
  version   = {0.1.0},
  url       = {https://github.com/sw176267788/FigSpec},
  license   = {MIT}
}
```

## 许可

MIT，见 [LICENSE](LICENSE)。
