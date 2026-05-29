"""Table and text helpers for GstarCAD COM automation."""

from __future__ import annotations

import csv
import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Sequence

from .types import PointLike

_ALL_TABLE_ROW_TYPES = 1 | 2 | 4


class FormatNotSupported(ValueError):
    """Raised when table import/export format is unsupported."""


class Table:
    """In-memory table with import/export helpers."""

    _write_formats = {"csv", "xls", "xlsx", "json"}
    _read_formats = {"csv", "xls", "xlsx", "json"}

    def __init__(self, rows: Iterable[Sequence[Any]] | None = None):
        self.rows: list[list[Any]] = [list(row) for row in rows] if rows else []

    def writerow(self, row: Sequence[Any]) -> None:
        self.rows.append(list(row))

    def append(self, row: Sequence[Any]) -> None:
        self.writerow(row)

    def clear(self) -> None:
        self.rows.clear()

    def convert(self, fmt: str) -> bytes:
        fmt = _normalize_format(fmt)
        self._raise_if_bad_write_format(fmt)
        if fmt == "json":
            return json.dumps(self.rows, ensure_ascii=False).encode("utf-8")
        if fmt == "csv":
            return _rows_to_csv_bytes(self.rows)
        return _rows_to_tablib_bytes(self.rows, fmt)

    def save(self, filename: str | Path, fmt: str | None = None, encoding: str = "cp1251") -> None:
        filename = Path(filename)
        fmt = _normalize_format(fmt or filename.suffix[1:])
        self._raise_if_bad_write_format(fmt)
        if fmt == "csv":
            with filename.open("w", newline="", encoding=encoding) as stream:
                writer = csv.writer(stream, delimiter=";")
                writer.writerows(self.rows)
            return
        filename.write_bytes(self.convert(fmt))

    def to_csv(self, stream: Any, encoding: str = "cp1251", delimiter: str = ";", **kwargs: Any) -> None:
        writer = csv.writer(_TextBinaryWriter(stream, encoding), delimiter=delimiter, **kwargs)
        writer.writerows(self.rows)

    def _raise_if_bad_write_format(self, fmt: str) -> None:
        if fmt not in self._write_formats:
            raise FormatNotSupported(f"Unknown format: {fmt}")

    @staticmethod
    def data_from_file(
        filename: str | Path,
        fmt: str | None = None,
        csv_encoding: str = "cp1251",
        csv_delimiter: str = ";",
    ) -> list[list[Any]]:
        filename = Path(filename)
        fmt = _normalize_format(fmt or filename.suffix[1:])
        if fmt not in Table._read_formats:
            raise FormatNotSupported(f"Unknown format: {fmt}")
        if fmt == "json":
            return json.loads(filename.read_text(encoding="utf-8"))
        if fmt == "csv":
            with filename.open("r", newline="", encoding=csv_encoding) as stream:
                return [row for row in csv.reader(stream, delimiter=csv_delimiter)]
        if fmt == "xlsx":
            return _read_xlsx(filename)
        return _read_xls(filename)

    @staticmethod
    def available_write_formats() -> list[str]:
        return sorted(Table._write_formats)

    @staticmethod
    def available_read_formats() -> list[str]:
        return sorted(Table._read_formats)


def create_table(
    context: Any,
    position: PointLike,
    *,
    rows: int | None = None,
    columns: int | None = None,
    data: Sequence[Sequence[Any]] | None = None,
    title: str | None = None,
    row_height: float = 8.0,
    col_width: float = 30.0,
    text_height: float | None = None,
    layer: str | None = None,
    color: int | None = None,
) -> Any:
    """Create and optionally populate a COM table."""
    if data is not None:
        data_rows = len(data)
        data_cols = max((len(row) for row in data), default=0)
    else:
        data_rows = 0
        data_cols = 0
    total_rows = rows if rows is not None else data_rows + (1 if title else 0)
    total_cols = columns if columns is not None else data_cols
    if total_rows <= 0 or total_cols <= 0:
        raise ValueError("table rows and columns must be positive")

    table = context.model.AddTable(context._point(position), total_rows, total_cols, row_height, col_width)
    if layer:
        context.ensure_layer(layer)
        table.Layer = layer
    if color is not None:
        table.Color = int(color)
    if text_height is not None:
        _set_table_text_height(table, float(text_height))

    start_row = 0
    if title is not None:
        set_cell_text(table, 0, 0, title)
        start_row = 1
    if data:
        for row_index, row in enumerate(data, start=start_row):
            for col_index, value in enumerate(row):
                if row_index < total_rows and col_index < total_cols:
                    set_cell_text(table, row_index, col_index, value)
    return table


def set_cell_text(table: Any, row: int, column: int, value: Any) -> None:
    """Set text in a table cell, supporting common COM table APIs."""
    text = "" if value is None else str(value)
    if hasattr(table, "SetText"):
        table.SetText(row, column, text)
        return
    table.SetCellValue(row, column, text)


def get_cell_text(table: Any, row: int, column: int) -> str:
    """Read text from a table cell."""
    if hasattr(table, "GetText"):
        return str(table.GetText(row, column))
    return str(table.GetCellValue(row, column))


@contextmanager
def suppress_regeneration(table: Any):
    """Temporarily suppress table regeneration."""
    table.RegenerateTableSuppressed = True
    try:
        yield table
    finally:
        table.RegenerateTableSuppressed = False


def text_width(text_item: Any) -> float:
    """Return the width of a Text or MText COM object from its bounding box."""
    get_bbox = getattr(text_item, "GetBoundingBox", None) or getattr(text_item, "GetBoundingbox")
    bbox_min, bbox_max = get_bbox()
    return float(bbox_max[0] - bbox_min[0])


def unformat_mtext(text: str, exclude_list: Iterable[str] = ("P", "S")) -> str:
    """Remove most AutoCAD/GstarCAD MText formatting control sequences."""
    excluded = "".join(exclude_list)
    text = re.sub(r"\{?\\[^%s][^;]+;" % excluded, "", text)
    return re.sub(r"\}", "", text)


def mtext_to_string(text: str) -> str:
    """Convert MText formatting into plain text with newlines."""
    return unformat_mtext(text).replace("\\P", "\n")


def string_to_mtext(text: str) -> str:
    """Escape plain text for basic MText usage."""
    return text.replace("\\", "\\\\").replace("\n", "\\P")


def _set_table_text_height(table: Any, value: float) -> None:
    setter = getattr(table, "SetTextHeight", None)
    if setter is not None:
        setter(_ALL_TABLE_ROW_TYPES, value)
        return
    cell_setter = getattr(table, "SetCellTextHeight", None)
    rows = int(getattr(table, "Rows", 0))
    columns = int(getattr(table, "Columns", 0))
    if cell_setter is not None and rows > 0 and columns > 0:
        for row in range(rows):
            for column in range(columns):
                cell_setter(row, column, value)
        return
    setattr(table, "TextHeight", value)


def _normalize_format(fmt: str) -> str:
    normalized = fmt.lower().lstrip(".")
    if normalized not in Table._write_formats | Table._read_formats:
        raise FormatNotSupported(f"Unknown format: {fmt}")
    return normalized


def _rows_to_csv_bytes(rows: Sequence[Sequence[Any]], encoding: str = "cp1251") -> bytes:
    import io

    stream = io.StringIO()
    writer = csv.writer(stream, delimiter=";")
    writer.writerows(rows)
    return stream.getvalue().encode(encoding)


def _rows_to_tablib_bytes(rows: Sequence[Sequence[Any]], fmt: str) -> bytes:
    try:
        import tablib
    except ImportError as exc:
        raise FormatNotSupported(f"{fmt} export requires optional dependency `tablib`") from exc
    dataset = tablib.Dataset()
    for row in rows:
        dataset.append(list(row))
    data = getattr(dataset, fmt)
    return data if isinstance(data, bytes) else data.encode("utf-8")


def _read_xls(filename: Path) -> list[list[Any]]:
    try:
        import xlrd
    except ImportError as exc:
        raise FormatNotSupported("xls import requires optional dependency `xlrd`") from exc
    book = xlrd.open_workbook(str(filename))
    sheet = book.sheet_by_index(0)
    return [[sheet.cell(row, col).value for col in range(sheet.ncols)] for row in range(sheet.nrows)]


def _read_xlsx(filename: Path) -> list[list[Any]]:
    try:
        import tablib
    except ImportError as exc:
        raise FormatNotSupported("xlsx import requires optional dependency `tablib[xlsx]`") from exc
    dataset = tablib.Dataset().load(filename.read_bytes(), format="xlsx")
    return [list(row) for row in dataset]


class _TextBinaryWriter:
    def __init__(self, stream: Any, encoding: str):
        self.stream = stream
        self.encoding = encoding

    def write(self, value: str) -> int:
        data = value.encode(self.encoding)
        self.stream.write(data)
        return len(value)


available_write_formats = Table.available_write_formats
available_read_formats = Table.available_read_formats
