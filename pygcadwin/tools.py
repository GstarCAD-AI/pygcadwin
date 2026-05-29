"""Agent-friendly JSON tool dispatch for pygcadwin."""

from __future__ import annotations

from typing import Any, Iterable

from .context import ComEntity, Context
from .exceptions import ToolDispatchError


_TOOL_SPECS: dict[str, dict[str, Any]] = {
    "create_segment": {
        "description": "Create a line segment in model space.",
        "required": ["start", "end"],
        "properties": {
            "start": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "end": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
            "lineweight": {"type": "integer"},
        },
    },
    "create_circle": {
        "description": "Create a circle in model space.",
        "required": ["center", "radius"],
        "properties": {
            "center": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "radius": {"type": "number"},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
            "lineweight": {"type": "integer"},
        },
    },
    "create_arc": {
        "description": "Create an arc. Angles are radians.",
        "required": ["center", "radius", "start_angle", "end_angle"],
        "properties": {
            "center": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "radius": {"type": "number"},
            "start_angle": {"type": "number"},
            "end_angle": {"type": "number"},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
            "lineweight": {"type": "integer"},
        },
    },
    "create_ellipse": {
        "description": "Create an ellipse. Rotation is radians.",
        "required": ["center", "semi_major", "semi_minor"],
        "properties": {
            "center": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "semi_major": {"type": "number"},
            "semi_minor": {"type": "number"},
            "rotation": {"type": "number"},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
            "lineweight": {"type": "integer"},
        },
    },
    "create_polyline": {
        "description": "Create a 3D polyline from vertices.",
        "required": ["vertices"],
        "properties": {
            "vertices": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            },
            "closed": {"type": "boolean"},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
            "lineweight": {"type": "integer"},
        },
    },
    "create_rect": {
        "description": "Create a rectangle from opposite corners.",
        "required": ["corner1", "corner2"],
        "properties": {
            "corner1": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "corner2": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
            "lineweight": {"type": "integer"},
        },
    },
    "create_text": {
        "description": "Create single-line text.",
        "required": ["position", "text", "height"],
        "properties": {
            "position": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "text": {"type": "string"},
            "height": {"type": "number"},
            "rotation_deg": {"type": "number"},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
        },
    },
    "create_hatch": {
        "description": "Create a hatch from boundary points or boundary entities.",
        "required": ["boundary"],
        "properties": {
            "boundary": {"type": "array"},
            "pattern_name": {"type": "string"},
            "scale": {"type": "number"},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
        },
    },
    "create_dimension": {
        "description": "Create an aligned dimension.",
        "required": ["pt1", "pt2", "dim_line_pt"],
        "properties": {
            "pt1": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "pt2": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "dim_line_pt": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "text": {"type": "string"},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
        },
    },
    "create_table": {
        "description": "Create and optionally populate a table.",
        "required": ["position"],
        "properties": {
            "position": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 3},
            "rows": {"type": "integer"},
            "columns": {"type": "integer"},
            "data": {"type": "array"},
            "title": {"type": "string"},
            "row_height": {"type": "number"},
            "col_width": {"type": "number"},
            "text_height": {"type": "number"},
            "layer": {"type": "string"},
            "color": {"type": "integer"},
        },
    },
    "ensure_layer": {
        "description": "Create or activate a layer.",
        "required": ["name"],
        "properties": {"name": {"type": "string"}, "color": {"type": "integer"}},
    },
    "list_layouts": {
        "description": "List layouts in tab order.",
        "required": [],
        "properties": {"skip_model": {"type": "boolean"}},
    },
    "iter_layout_entities": {
        "description": "List entities from model space or a named layout.",
        "required": [],
        "properties": {
            "layout": {"type": "string"},
            "object_name_or_list": {"type": ["string", "array"]},
            "limit": {"type": "integer"},
        },
    },
    "select_filter": {
        "description": "Select entities matching a filter dictionary.",
        "required": ["filter_dict"],
        "properties": {
            "filter_dict": {"type": "object"},
            "layout": {"type": "string"},
        },
    },
    "save_as": {
        "description": "Save the active drawing to a path.",
        "required": ["path"],
        "properties": {"path": {"type": "string"}},
    },
    "regen": {
        "description": "Regenerate the active document.",
        "required": [],
        "properties": {"mode": {"type": "integer"}},
    },
    "zoom_extents": {
        "description": "Zoom to drawing extents.",
        "required": [],
        "properties": {},
    },
    "snapshot": {
        "description": "Capture the current GstarCAD viewport to a PNG file.",
        "required": ["path"],
        "properties": {
            "path": {"type": "string"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
        },
    },
}


def tool_schemas() -> list[dict[str, Any]]:
    """Return JSON-schema tool descriptors for supported operations."""
    schemas = []
    for name, spec in _TOOL_SPECS.items():
        schemas.append(
            {
                "name": name,
                "description": spec["description"],
                "parameters": {
                    "type": "object",
                    "properties": spec["properties"],
                    "required": spec["required"],
                },
            }
        )
    return schemas


def execute_tool(
    name: str,
    args: dict[str, Any] | None = None,
    *,
    context: Context | None = None,
) -> dict[str, Any]:
    """Validate and execute one tool call."""
    if name not in _TOOL_SPECS:
        raise ToolDispatchError(f"Unknown pygcadwin tool: {name}")
    args = dict(args or {})
    spec = _TOOL_SPECS[name]
    missing = [param for param in spec["required"] if param not in args]
    if missing:
        raise ToolDispatchError(f"Tool {name!r} missing required args: {', '.join(missing)}")
    context = context or Context.current()

    result = _execute(context, name, args)
    return {"ok": True, "tool": name, "result": _serialize_result(result)}


def run_actions(
    actions: Iterable[dict[str, Any]],
    *,
    context: Context | None = None,
) -> list[dict[str, Any]]:
    """Execute a sequence of ``{'name': ..., 'args': ...}`` actions."""
    context = context or Context.current()
    results = []
    for action in actions:
        results.append(execute_tool(action["name"], action.get("args", {}), context=context))
    return results


def _serialize_result(value: Any) -> Any:
    if isinstance(value, ComEntity):
        return value.to_result()
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_result(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_result(item) for key, item in value.items()}
    return {
        "name": str(getattr(value, "Name", "")) or None,
        "handle": str(getattr(value, "Handle", "")) or None,
        "object_name": str(getattr(value, "ObjectName", "")) or None,
        "layer": str(getattr(value, "Layer", "")) or None,
        "color": getattr(value, "Color", None),
    }


def _execute(context: Context, name: str, args: dict[str, Any]) -> Any:
    if name == "list_layouts":
        from .layouts import iter_layouts

        return [
            {"name": layout.Name, "tab_order": layout.TabOrder}
            for layout in iter_layouts(context.document, skip_model=args.get("skip_model", True))
        ]
    if name == "iter_layout_entities":
        from .layouts import iter_layout_entities

        return list(iter_layout_entities(context.document, **args))
    if name == "select_filter":
        from .selection import select_filter

        return select_filter(context.document, **args)
    if name == "snapshot":
        path = args["path"]
        snapshot = context.view.snapshot(width=args.get("width"), height=args.get("height"))
        snapshot.save(path)
        return {"path": path, "width": snapshot.width, "height": snapshot.height, "mode": snapshot.mode}
    method = getattr(context, name)
    return method(**args)
