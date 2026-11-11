"""The rule registry and every bundled rule.

Rules are small, pure functions over a :class:`LintContext`.  Each one is
registered with a stable code and a default severity, which lets users silence
individual findings (``--ignore CO002``) or lower the failure threshold without
patching figspec.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

from ..palette import contrast_ratio, is_rainbow, parse_color, simulate_pair_distance
from ..palette.color import delta_e_ciede2000, rgb_to_lab
from .context import LintContext
from .report import Finding

__all__ = ["RULE_REGISTRY", "RuleMeta", "all_rule_codes", "rule"]

VECTOR_FORMATS = frozenset({"pdf", "svg", "eps"})
RASTER_EXTENSIONS = frozenset({"png", "jpg", "tif"})


@dataclass(frozen=True)
class RuleMeta:
    """Documentation and default severity for one rule."""

    code: str
    title: str
    severity: str
    description: str
    func: Callable[[LintContext], Iterable[Finding]]


RULE_REGISTRY: dict[str, RuleMeta] = {}


def rule(
    code: str,
    title: str,
    severity: str = "warning",
    description: str = "",
) -> Callable[[Callable[[LintContext], list[Finding]]], Callable[[LintContext], list[Finding]]]:
    """Register a lint rule under ``code``."""

    def decorator(
        func: Callable[[LintContext], list[Finding]],
    ) -> Callable[[LintContext], list[Finding]]:
        if code in RULE_REGISTRY:  # pragma: no cover - developer error
            raise ValueError(f"duplicate lint rule code '{code}'")
        RULE_REGISTRY[code] = RuleMeta(
            code=code,
            title=title,
            severity=severity,
            description=description or title,
            func=func,
        )
        return func

    return decorator


def _finding(
    code: str,
    message: str,
    *,
    hint: str | None = None,
    severity: str | None = None,
    **detail: object,
) -> Finding:
    meta = RULE_REGISTRY[code]
    return Finding(
        code=code,
        severity=severity or meta.severity,
        message=message,
        hint=hint,
        detail=detail,
        rule_title=meta.title,
    )


def all_rule_codes() -> tuple[str, ...]:
    return tuple(sorted(RULE_REGISTRY))


# ---------------------------------------------------------------------------
# typography
# ---------------------------------------------------------------------------


@rule(
    "FS001",
    "Text is smaller than the minimum readable size",
    "error",
    "Every text object must stay legible at the final printed size; journals commonly "
    "require at least 5 pt.",
)
def check_font_size(ctx: LintContext) -> list[Finding]:
    minimum = ctx.min_font_size
    offenders = [text for text in ctx.texts if text.get_fontsize() < minimum - 1e-9]
    if not offenders:
        return []
    smallest = min(text.get_fontsize() for text in offenders)
    example = offenders[0].get_text()[:36]
    return [
        _finding(
            "FS001",
            f"{len(offenders)} text element(s) render at {smallest:g} pt, "
            f"below the {minimum:g} pt minimum",
            hint=f"raise font_size, shorten tick labels, or drop the label '{example}'",
            count=len(offenders),
            smallest=smallest,
            minimum=minimum,
        )
    ]


@rule(
    "FS002",
    "A line is thinner than the minimum stroke width",
    "warning",
    "Hairlines disappear in print and when figures are scaled down.",
)
def check_line_width(ctx: LintContext) -> list[Finding]:
    minimum = ctx.style.min_line_width
    thin = [line for line in ctx.lines if line.get_linewidth() < minimum - 1e-9]
    if not thin:
        return []
    smallest = min(line.get_linewidth() for line in thin)
    return [
        _finding(
            "FS002",
            f"{len(thin)} line(s) are {smallest:g} pt wide, below the {minimum:g} pt minimum",
            hint="increase line width in style/line settings",
            count=len(thin),
            smallest=smallest,
            minimum=minimum,
        )
    ]


@rule(
    "FS003",
    "Figure width does not match the journal column",
    "warning",
    "Printing at the wrong width rescales every font and stroke, undoing the careful sizing.",
)
def check_figure_width(ctx: LintContext) -> list[Finding]:
    journal = ctx.journal
    if journal is None:
        return []
    layout = ctx.spec.figure.layout
    target = journal.width_for(layout)
    if target is None:
        return []
    width = ctx.style.width
    deviation = abs(width - target) / target
    if deviation <= 0.02:
        return []
    return [
        _finding(
            "FS003",
            f"figure is {width:.2f} in wide, but the {journal.display_name} "
            f"{layout} column is {target:.2f} in ({deviation:.0%} off)",
            hint=f"use 'layout: {layout}' without an explicit size, or set size to {target:.2f} in",
            width=round(width, 4),
            target=round(target, 4),
            deviation=round(deviation, 4),
        )
    ]


@rule(
    "FS004",
    "Figure is taller than the journal allows",
    "warning",
    "Figures that exceed the page height are shrunk on import, which breaks font sizes.",
)
def check_figure_height(ctx: LintContext) -> list[Finding]:
    journal = ctx.journal
    if journal is None or journal.max_height is None:
        return []
    height = ctx.style.height
    if height <= journal.max_height + 1e-9:
        return []
    return [
        _finding(
            "FS004",
            f"figure is {height:.2f} in tall, above the {journal.max_height:.2f} in maximum",
            hint="reduce 'aspect', split the figure into panels, or move detail to the supplement",
            height=round(height, 4),
            maximum=journal.max_height,
        )
    ]


# ---------------------------------------------------------------------------
# colour
# ---------------------------------------------------------------------------


@rule(
    "CO001",
    "A series colour has too little contrast with the background",
    "warning",
    "The WCAG 2.1 3:1 threshold is a good proxy for whether a thin line survives print.",
)
def check_contrast(ctx: LintContext) -> list[Finding]:
    background = parse_color(ctx.style.background)
    offenders = []
    for color in ctx.thin_colors[:24]:
        ratio = contrast_ratio(parse_color(color), background)
        if ratio < 3.0:
            offenders.append((color, ratio))
    if not offenders:
        return []
    offenders.sort(key=lambda item: item[1])
    color, ratio = offenders[0]
    return [
        _finding(
            "CO001",
            f"{len(offenders)} series colour(s) fall below 3:1 contrast; "
            f"{color} is the weakest at {ratio:.2f}:1",
            hint="darken the colour, or add a marker/hatch so the series does not rely on hue alone",
            colors=[item[0] for item in offenders],
        )
    ]


@rule(
    "CO002",
    "Colours become indistinguishable with colour-vision deficiency",
    "warning",
    "Roughly 8% of men cannot separate red and green; simulated CIEDE2000 below 6 means the "
    "pair will look the same.",
)
def check_color_vision(ctx: LintContext) -> list[Finding]:
    colors = list(dict.fromkeys(ctx.colors))[:12]
    problems: list[tuple[str, str, float]] = []
    for index, first in enumerate(colors):
        for second in colors[index + 1 :]:
            original = delta_e_ciede2000(rgb_to_lab(parse_color(first)), rgb_to_lab(parse_color(second)))
            if original < 6.0:
                continue
            simulated = min(
                simulate_pair_distance(first, second, kind)
                for kind in ("deuteranopia", "protanopia")
            )
            if simulated < 6.0:
                problems.append((first, second, simulated))
    if not problems:
        return []
    first, second, distance = min(problems, key=lambda item: item[2])
    more = f" (+{len(problems) - 1} more pair(s))" if len(problems) > 1 else ""
    return [
        _finding(
            "CO002",
            f"{first} and {second} collapse to ΔE00 {distance:.1f} under deuteranopia/protanopia{more}",
            hint="pick a colour-blind safe palette (okabe-ito, tol-bright, ibm) or add distinct markers",
            pairs=[[item[0], item[1], round(item[2], 2)] for item in problems[:5]],
        )
    ]


@rule(
    "CO003",
    "Heatmap uses a rainbow colormap",
    "warning",
    "Rainbow maps create phantom boundaries and are not perceptually ordered.",
)
def check_colormap(ctx: LintContext) -> list[Finding]:
    found: list[str] = []
    for panel in ctx.spec.panels:
        for series in panel.series:
            if series.kind != "heatmap":
                continue
            cmap = series.cmap
            if cmap is None:
                palette = ctx.style.palette
                cmap = palette.name if palette.kind == "sequential" else "viridis"
            if is_rainbow(cmap):
                found.append(cmap)
    if not found:
        return []
    return [
        _finding(
            "CO003",
            f"rainbow-style colormap(s) in use: {', '.join(sorted(set(found)))}",
            hint="use 'viridis', 'cividis' or a single-hue map such as 'Blues'",
        )
    ]


@rule(
    "CO004",
    "More series colours than the palette can carry",
    "info",
    "Beyond about eight hues readers cannot map colours back to a legend.",
)
def check_color_count(ctx: LintContext) -> list[Finding]:
    limit = ctx.journal.max_colors if ctx.journal else 8
    count = len(ctx.colors)
    if count <= limit:
        return []
    return [
        _finding(
            "CO004",
            f"{count} series colours exceed the recommended {limit}",
            hint="facet the series into panels, use a sequential encoding, or highlight only a few",
            count=count,
            limit=limit,
        )
    ]


# ---------------------------------------------------------------------------
# structure and output
# ---------------------------------------------------------------------------


@rule(
    "ST001",
    "No vector format is produced",
    "warning",
    "Raster-only output cannot be edited or re-scaled by the typesetter.",
)
def check_vector_output(ctx: LintContext) -> list[Finding]:
    formats = ctx.style.formats
    if any(item in VECTOR_FORMATS for item in formats):
        return []
    return [
        _finding(
            "ST001",
            f"only raster formats are configured ({', '.join(formats)})",
            hint="add 'pdf' or 'svg' to figure.formats",
            formats=list(formats),
        )
    ]


@rule(
    "ST002",
    "Raster resolution is below the journal requirement",
    "error",
    "Journals reject figures that cannot be reproduced at print resolution.",
)
def check_raster_dpi(ctx: LintContext) -> list[Finding]:
    required = ctx.journal.raster_dpi if ctx.journal else 300
    dpi = ctx.style.dpi
    if dpi >= required:
        return []
    return [
        _finding(
            "ST002",
            f"raster output is {dpi} dpi, below the {required} dpi minimum",
            hint="raise 'figure.dpi' or drop raster output entirely",
            dpi=dpi,
            required=required,
        )
    ]


@rule(
    "ST003",
    "Multiple labelled series but no legend",
    "warning",
    "Without a legend the reader cannot decode the series.",
)
def check_legend(ctx: LintContext) -> list[Finding]:
    labelled = sum(
        len(series.labels or ()) for panel in ctx.prepared.panels for series in panel.series
    )
    if labelled < 2:
        return []
    if any(axes.get_legend() is not None for axes in ctx.figure.axes):
        return []
    return [
        _finding(
            "ST003",
            f"{labelled} labelled data series are drawn but no legend is rendered",
            hint="add a legend block, or set legend.show: true if it was disabled",
            labelled=labelled,
        )
    ]


@rule(
    "ST004",
    "Axis has no label",
    "info",
    "Unlabelled axes are the most common reviewer comment on figures.",
)
def check_axis_labels(ctx: LintContext) -> list[Finding]:
    if len(ctx.spec.panels) != 1:
        return []
    panel = ctx.spec.panels[0]
    if all(series.kind == "heatmap" for series in panel.series):
        return []
    findings: list[Finding] = []
    for name in ("x", "y"):
        axis = panel.axes.get(name)
        hidden = axis.hide if axis is not None else False
        label = axis.label if axis is not None else None
        if not hidden and not label:
            findings.append(
                _finding(
                    "ST004",
                    f"the {name} axis has no label",
                    hint="describe the quantity and its unit, for example 'Time (s)'",
                    axis=name,
                )
            )
    return findings


@rule(
    "ST005",
    "Figure is drawn with a closed frame",
    "info",
    "Most journals prefer open axes; a full box adds ink without adding information.",
)
def check_frame(ctx: LintContext) -> list[Finding]:
    spines = set(ctx.style.spines)
    if {"left", "right", "top", "bottom"} - spines:
        return []
    return [
        _finding(
            "ST005",
            "all four spines are visible",
            hint="set 'spines: [left, bottom]' in the style block",
        )
    ]


@rule(
    "ST006",
    "Line series has fewer than two points",
    "warning",
    "A single point hides the trend and usually signals a data or slicing bug.",
)
def check_short_series(ctx: LintContext) -> list[Finding]:
    findings: list[Finding] = []
    for panel_index, panel in enumerate(ctx.prepared.panels):
        for series_index, series in enumerate(panel.series):
            if series.kind in ("line", "area", "errorbar") and len(series.x) < 2:
                findings.append(
                    _finding(
                        "ST006",
                        f"series {panel_index}.{series_index} has {len(series.x)} point(s)",
                        hint="check the data selection, or draw the point with type 'scatter'",
                        panel=panel_index,
                        series=series_index,
                    )
                )
    return findings


@rule(
    "ST007",
    "Categorical axis has more labels than it can show",
    "warning",
    "More than twelve category labels overlap at column width.",
)
def check_crowded_ticks(ctx: LintContext) -> list[Finding]:
    findings: list[Finding] = []
    for panel in ctx.prepared.panels:
        for series in panel.series:
            if not series.is_categorical:
                continue
            categories = int(len(np.unique(np.asarray(series.x, dtype=object))))
            if categories > 12:
                findings.append(
                    _finding(
                        "ST007",
                        f"{categories} category labels will overlap on the x axis",
                        hint="rotate labels with params.x_rotation, shorten them, or use a horizontal bar chart",
                        categories=categories,
                    )
                )
                break
    return findings


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------


@rule(
    "DA001",
    "Data contains missing values",
    "info",
    "NaNs render as gaps and can mask a failed join or a silently truncated sweep.",
)
def check_missing_values(ctx: LintContext) -> list[Finding]:
    missing = 0
    for panel in ctx.prepared.panels:
        for series in panel.series:
            for values in series.ys:
                missing += int(np.isnan(np.asarray(values, dtype=float)).sum())
    if missing == 0:
        return []
    return [
        _finding(
            "DA001",
            f"{missing} missing value(s) will appear as gaps",
            hint="drop or impute those rows upstream if the gap is not meaningful",
            count=missing,
        )
    ]


@rule(
    "DA002",
    "Legend labels are duplicated",
    "warning",
    "Duplicate labels make the legend ambiguous; only the first entry is kept.",
)
def check_duplicate_labels(ctx: LintContext) -> list[Finding]:
    findings: list[Finding] = []
    for panel_index, panel in enumerate(ctx.prepared.panels):
        labels = [label for series in panel.series for label in (series.labels or ())]
        duplicates = sorted({label for label in labels if labels.count(label) > 1})
        if duplicates:
            findings.append(
                _finding(
                    "DA002",
                    f"duplicate legend label(s): {', '.join(duplicates[:3])}",
                    hint="give every series a unique 'label'",
                    panel=panel_index,
                    labels=duplicates,
                )
            )
    return findings


@rule(
    "DA003",
    "Bar chart axis is truncated",
    "warning",
    "Bar length encodes the value, so cutting the axis exaggerates differences. "
    "Use a dot plot, or start the axis at zero.",
)
def check_truncated_bars(ctx: LintContext) -> list[Finding]:
    findings: list[Finding] = []
    for panel_index, panel in enumerate(ctx.spec.panels):
        if not any(series.kind == "bar" for series in panel.series):
            continue
        axis = panel.axes.get("y")
        if axis is None or axis.limits is None:
            continue
        low, high = axis.limits
        if low > 0 or high < 0:
            findings.append(
                _finding(
                    "DA003",
                    f"panel {panel_index} bars start at {low:g} instead of zero",
                    hint="set the y limit to 0, or switch the series to 'errorbar' "
                    "(a dot plot does not imply a zero baseline)",
                    panel=panel_index,
                    limits=[low, high],
                )
            )
    return findings
