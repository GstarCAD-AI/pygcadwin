"""Layout and block helpers for GstarCAD COM documents."""

from __future__ import annotations

from typing import Any, Iterable

from .context import _iter_com_collection


def unwrap_document(document: Any) -> Any:
    """Return the raw COM document from either a wrapper or raw COM object."""
    return document.raw if hasattr(document, "raw") else document


def iter_layouts(document: Any, *, skip_model: bool = True) -> Iterable[Any]:
    """Iterate layouts ordered by ``TabOrder``.

    Args:
        document: ``pygcadwin.Document`` or raw COM document.
        skip_model: omit model-space layout when true.
    """
    raw_doc = unwrap_document(document)
    layouts = sorted(_iter_com_collection(raw_doc.Layouts), key=lambda layout: layout.TabOrder)
    for layout in layouts:
        if skip_model and int(getattr(layout, "TabOrder", 0)) == 0:
            continue
        yield layout


def get_model_space(document: Any) -> Any:
    """Return the document model-space block."""
    return unwrap_document(document).ModelSpace


def get_paper_space(document: Any, layout: str | None = None) -> Any:
    """Return a paper-space layout block.

    When ``layout`` is omitted, the active layout block is returned unless it
    is model space; in that case the first paper-space layout is used.
    """
    raw_doc = unwrap_document(document)
    if layout is not None:
        for candidate in iter_layouts(raw_doc, skip_model=False):
            if str(getattr(candidate, "Name", "")).lower() == layout.lower():
                return candidate.Block
        raise KeyError(f"Layout not found: {layout}")

    active = getattr(raw_doc, "ActiveLayout", None)
    if active is not None and int(getattr(active, "TabOrder", 0)) != 0:
        return active.Block

    for candidate in iter_layouts(raw_doc):
        return candidate.Block
    raise RuntimeError("No paper-space layout is available")


def iter_layout_entities(
    document: Any,
    *,
    layout: str | None = None,
    object_name_or_list: str | Iterable[str] | None = None,
    limit: int | None = None,
) -> Iterable[Any]:
    """Iterate entities from model space or a named paper-space layout."""
    from .selection import iter_objects

    raw_doc = unwrap_document(document)
    block = raw_doc.ModelSpace if layout is None else get_paper_space(raw_doc, layout)
    return iter_objects(raw_doc, object_name_or_list, block=block, limit=limit)

