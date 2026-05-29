"""pyautocad-style object iteration and selection helpers."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .context import _iter_com_collection
from .layouts import get_paper_space, unwrap_document


def iter_objects(
    document: Any,
    object_name_or_list: str | Iterable[str] | None = None,
    *,
    block: Any | None = None,
    limit: int | None = None,
    dont_cast: bool = False,
    best_interface: Callable[[Any], Any] | None = None,
) -> Iterable[Any]:
    """Iterate COM objects from a block or the active layout block."""
    if block is None:
        block = document.ActiveLayout.Block
    names = object_name_or_list
    if isinstance(names, str):
        lowered_names = [names.lower()]
    elif names is None:
        lowered_names = []
    else:
        lowered_names = [name.lower() for name in names]

    yielded = 0
    for item in _iter_com_collection(block):
        if limit is not None and yielded >= limit:
            return
        object_name = str(getattr(item, "ObjectName", "")).lower()
        if lowered_names and not any(name in object_name for name in lowered_names):
            continue
        if not dont_cast and best_interface is not None:
            item = best_interface(item)
        yielded += 1
        yield item


def find_one(
    document: Any,
    object_name_or_list: str | Iterable[str],
    *,
    block: Any | None = None,
    predicate: Callable[[Any], bool] | None = None,
    best_interface: Callable[[Any], Any] | None = None,
) -> Any | None:
    """Return the first object matching type/name and predicate."""
    predicate = predicate or bool
    for obj in iter_objects(document, object_name_or_list, block=block, best_interface=best_interface):
        if predicate(obj):
            return obj
    return None


def get_selection(document: Any, name: str = "PYGCADWIN_SELECTION", prompt: str | None = None) -> Any:
    """Ask the user to select objects on screen."""
    raw_doc = unwrap_document(document)
    if prompt:
        raw_doc.Utility.Prompt(f"{prompt}\n")
    selection = create_selection_set(raw_doc, name, replace=True)
    selection.SelectOnScreen()
    return selection


def create_selection_set(document: Any, name: str, *, replace: bool = True) -> Any:
    """Create a named selection set, optionally replacing an existing set."""
    raw_doc = unwrap_document(document)
    if replace:
        delete_selection_set(raw_doc, name)
    return raw_doc.SelectionSets.Add(name)


def delete_selection_set(document: Any, name: str) -> bool:
    """Delete a named selection set if it exists."""
    raw_doc = unwrap_document(document)
    try:
        raw_doc.SelectionSets.Item(name).Delete()
        return True
    except Exception:
        return False


def select_filter(
    document: Any,
    filter_dict: dict[str, Any],
    *,
    layout: str | None = None,
    block: Any | None = None,
) -> list[Any]:
    """Return COM entities matching all supported filter keys.

    Supported keys: ``object_name``/``class_name``, ``layer``, ``color``,
    ``linetype``.
    """
    candidates = _selection_candidates(document, layout=layout, block=block)
    return [entity for entity in candidates if _matches_filter(entity, filter_dict)]


def select_predicate(
    document: Any,
    predicate: Callable[[Any], bool],
    *,
    layout: str | None = None,
    block: Any | None = None,
) -> list[Any]:
    """Return COM entities for which ``predicate(entity)`` is true."""
    return [entity for entity in _selection_candidates(document, layout=layout, block=block) if predicate(entity)]


def _selection_candidates(document: Any, *, layout: str | None = None, block: Any | None = None):
    raw_doc = unwrap_document(document)
    if block is not None:
        return iter_objects(raw_doc, block=block)
    if layout is not None:
        return iter_objects(raw_doc, block=get_paper_space(raw_doc, layout))
    return iter_objects(raw_doc, block=raw_doc.ModelSpace)


def _matches_filter(entity: Any, filter_dict: dict[str, Any]) -> bool:
    for key, wanted in filter_dict.items():
        if key in ("object_name", "class_name"):
            actual = getattr(entity, "ObjectName", "")
            if str(actual).lower() != str(wanted).lower():
                return False
        elif key == "layer":
            if str(getattr(entity, "Layer", "")).lower() != str(wanted).lower():
                return False
        elif key == "color":
            if int(getattr(entity, "Color", -1)) != int(wanted):
                return False
        elif key == "linetype":
            if str(getattr(entity, "Linetype", "")).lower() != str(wanted).lower():
                return False
        else:
            raise ValueError(f"Unsupported selection filter key: {key}")
    return True
