"""Everything the lint rules can inspect, collected once per figure."""

from __future__ import annotations

from dataclasses import dataclass

from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Text

from ..data.series import PreparedFigure
from ..journals import JournalPreset
from ..render.figure import RenderResult
from ..render.theme import ResolvedStyle
from ..spec.schema import Spec

__all__ = ["LintContext", "make_context"]


@dataclass(frozen=True)
class LintContext:
    """A built figure plus materialised artists, ready for inspection."""

    result: RenderResult
    texts: tuple[Text, ...]
    lines: tuple[Line2D, ...]

    @property
    def spec(self) -> Spec:
        return self.result.spec

    @property
    def figure(self) -> Figure:
        return self.result.figure

    @property
    def style(self) -> ResolvedStyle:
        return self.result.style

    @property
    def journal(self) -> JournalPreset | None:
        return self.result.journal

    @property
    def prepared(self) -> PreparedFigure:
        return self.result.prepared

    @property
    def colors(self) -> tuple[str, ...]:
        return self.result.series_colors

    @property
    def thin_colors(self) -> tuple[str, ...]:
        """Colours used for lines, markers and error bars (thin marks)."""
        return self.result.thin_colors

    @property
    def min_font_size(self) -> float:
        return self.style.min_font_size


def make_context(result: RenderResult) -> LintContext:
    """Walk the figure once and snapshot the artists rules care about."""
    figure = result.figure
    texts = tuple(text for text in figure.findobj(Text) if text.get_text().strip())
    lines = tuple(figure.findobj(Line2D))
    return LintContext(result=result, texts=texts, lines=lines)
