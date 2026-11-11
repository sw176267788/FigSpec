<div align="center">

<img src="docs/assets/hero.png" alt="由 YAML 规格渲染出的六张投稿级科研图" width="780">

# figspec

**把图当代码来管：声明式、期刊合规、可复现的科研绘图工具链。**

[![CI](https://github.com/sw176267788/FigSpec/actions/workflows/ci.yml/badge.svg)](https://github.com/sw176267788/FigSpec/actions/workflows/ci.yml)
[![Docs](https://github.com/sw176267788/FigSpec/actions/workflows/docs.yml/badge.svg)](https://sw176267788.github.io/FigSpec/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776ab.svg)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f.svg)](LICENSE)

[English](README.md) · [简体中文](README.zh-CN.md)

</div>

figspec 把一份很小的 YAML 编译成可直接投稿的图：它会按目标期刊解析栏宽、字体、
线宽与 DPI，输出 PDF/SVG/PNG，检查字号与配色是否可读，并记录一份可校验的溯源
清单。

```bash
figspec render figure.yaml -o figures     # → figures/figure.{pdf,svg,png}
figspec lint   figure.yaml --journal nature
figspec verify figures/figure.figspec.json
```

## 特性

- **声明式规格**：尺寸、坐标轴、数据系列、图例、注释、多子图布局写在一个
  YAML/JSON 里，可 diff、可评审。
- **8 套期刊预设**：Nature、Science、Cell、IEEE、ACM、Elsevier、Springer、PLOS，
  也可用 `--journal-file` 加载自定义预设。
- **18 条 lint 规则**：最终尺寸下的最小字号、线宽、WCAG 对比度、色盲可分辨性、
  DPI、图例与坐标轴标签、彩虹色图、截断的柱状图坐标轴。
- **可复现输出**：同一环境下 PDF/SVG/PNG/EPS 逐字节一致。
- **溯源清单**：每次构建记录输入与输出哈希、依赖版本、git 状态；
  `figspec verify` 检测漂移。
- **多子图**：显式或自动网格、共享坐标轴、`(a)`–`(d)` 标号、逐面板图例。
- **可接入 CI**：`--strict`、`--fail-on`、JSON 与 SARIF 2.1.0 输出。
- **库优先**：CLI 背后是带类型的 Python API。

## 安装

figspec 尚未发布到 PyPI，请从仓库安装：

```bash
pip install "git+https://github.com/sw176267788/FigSpec.git"
```

或者克隆后开发：

```bash
git clone https://github.com/sw176267788/FigSpec.git
cd FigSpec
pip install -e ".[dev]"
pytest -q
```

需要 **Python 3.10+** 与 matplotlib 3.7+；运行时依赖只有 matplotlib、numpy、
PyYAML、click。

## 快速开始

```bash
figspec init my-paper                     # 生成 figure.yaml 与 data/loss.csv
figspec render my-paper/figure.yaml -o figures
figspec lint   my-paper/figure.yaml --journal nature
```

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
`extends` 继承，字符串支持 `${ENV}` 插值。完整字段说明见
[docs/spec-reference.md](docs/spec-reference.md)。

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

`figspec lint` 会先构建图，再检查真实图元并给出带稳定编号的结论：

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

报告支持 text / JSON / SARIF 2.1.0；每条规则的说明见
[docs/lint-rules.md](docs/lint-rules.md)。

## 可复现构建

每次构建都会在产物旁写下 `<stem>.figspec.json`，记录规格哈希、每个输入文件的
SHA-256、输出哈希与 DPI、依赖版本以及 git 提交：

```
$ figspec verify figures/figure.figspec.json
verifying figures/figure.figspec.json
  OK   schema: figspec/provenance/v1
  OK   spec: figure.yaml matches
  OK   input loss.csv: loss.csv matches
  OK   output figure.pdf: figure.pdf matches
  OK   environment: tool versions match
```

同一环境下 PDF/SVG/PNG/EPS 的渲染结果是确定的，重建要么完全一致，要么明确告诉
你哪里变了。详见 [docs/provenance.md](docs/provenance.md)。

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

完整参数与退出码见 [docs/cli.md](docs/cli.md)。

## Python API

```python
import figspec

outcome = figspec.render("figure.yaml", "out/", journal="nature", strict=True)
print(outcome.report.to_text())
for output in outcome.outputs:
    print(output.path, output.sha256[:12])
outcome.close()
```

底层入口：`figspec.load_spec`、`figspec.render.build`、`figspec.render.export`、
`figspec.lint.lint_result`、`figspec.provenance.create_manifest`。

## 文档

| 页面 | 内容 |
|---|---|
| [快速开始](docs/quickstart.md) | 从安装到第一张图 |
| [图库](docs/gallery.md) | 六张完整示例图及其规格 |
| [规格参考](docs/spec-reference.md) | 所有字段与默认值 |
| [期刊预设](docs/journals.md) | 每套预设约束了什么 |
| [Lint 规则](docs/lint-rules.md) | 18 条规则及其理由 |
| [溯源](docs/provenance.md) | 清单格式与校验方式 |
| [CLI](docs/cli.md) | 命令、参数与退出码 |
| [配方](docs/recipes.md) | 常见图的写法 |
| [FAQ](docs/faq.md) | 对比、字体、notebook |

## 许可

MIT，见 [LICENSE](LICENSE)。
