"""Context-scoped CAD operations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from .document import Document
from .types import PointLike, point_tuple, variant_dispatch_array, variant_doubles, variant_point


@dataclass
class ComEntity:
    """Lightweight wrapper around a COM entity."""

    raw: Any

    @property
    def handle(self) -> str | None:
        value = getattr(self.raw, "Handle", None)
        return None if value is None else str(value)

    @property
    def object_name(self) -> str:
        return str(getattr(self.raw, "ObjectName", ""))

    @property
    def layer(self) -> str | None:
        value = getattr(self.raw, "Layer", None)
        return None if value is None else str(value)

    @property
    def color(self) -> int | None:
        value = getattr(self.raw, "Color", None)
        return None if value is None else int(value)

    def to_result(self) -> dict[str, Any]:
        return {
            "handle": self.handle,
            "object_name": self.object_name,
            "layer": self.layer,
            "color": self.color,
        }


class Context:
    """Creator and document helper methods bound to one CAD document."""

    def __init__(self, document: Document):
        self.document = document

    @classmethod
    def current(cls, *, create_if_missing: bool = True, visible: bool = True) -> "Context":
        from .api import Gcad

        return Gcad(create_if_missing=create_if_missing, visible=visible).context

    @property
    def doc(self) -> Any:
        return self.document.raw

    @property
    def model(self) -> Any:
        return self.document.model_space

    @property
    def view(self) -> Any:
        from .view import View

        return View(self)

    @property
    def _com_client(self) -> Any | None:
        owner = getattr(self.document, "_owner", None)
        return getattr(owner, "_com_client", None)

    @property
    def _pythoncom(self) -> Any | None:
        owner = getattr(self.document, "_owner", None)
        return getattr(owner, "_pythoncom", None)

    def create_segment(
        self,
        start: PointLike,
        end: PointLike,
        *,
        color: int | None = None,
        layer: str | None = None,
        lineweight: int | None = None,
        **_: Any,
    ) -> ComEntity:
        entity = self.model.AddLine(self._point(start), self._point(end))
        return self._style_entity(entity, color=color, layer=layer, lineweight=lineweight)

    def create_circle(
        self,
        center: PointLike,
        radius: float,
        *,
        color: int | None = None,
        layer: str | None = None,
        lineweight: int | None = None,
        **_: Any,
    ) -> ComEntity:
        entity = self.model.AddCircle(self._point(center), float(radius))
        return self._style_entity(entity, color=color, layer=layer, lineweight=lineweight)

    def create_arc(
        self,
        center: PointLike,
        radius: float,
        start_angle: float,
        end_angle: float,
        *,
        ccw: bool = True,
        color: int | None = None,
        layer: str | None = None,
        lineweight: int | None = None,
        **_: Any,
    ) -> ComEntity:
        del ccw
        entity = self.model.AddArc(
            self._point(center),
            float(radius),
            float(start_angle),
            float(end_angle),
        )
        return self._style_entity(entity, color=color, layer=layer, lineweight=lineweight)

    def create_ellipse(
        self,
        center: PointLike,
        semi_major: float,
        semi_minor: float,
        *,
        rotation: float = 0.0,
        color: int | None = None,
        layer: str | None = None,
        lineweight: int | None = None,
        **_: Any,
    ) -> ComEntity:
        if semi_major == 0:
            raise ValueError("semi_major must be non-zero")
        major_vector = (
            float(semi_major) * math.cos(float(rotation)),
            float(semi_major) * math.sin(float(rotation)),
            0.0,
        )
        entity = self.model.AddEllipse(
            self._point(center),
            self._point(major_vector),
            float(semi_minor) / float(semi_major),
        )
        return self._style_entity(entity, color=color, layer=layer, lineweight=lineweight)

    def create_polyline(
        self,
        vertices: Sequence[PointLike],
        *,
        closed: bool = False,
        color: int | None = None,
        layer: str | None = None,
        lineweight: int | None = None,
        **_: Any,
    ) -> ComEntity:
        coords = [coord for point in vertices for coord in point_tuple(point)]
        entity = self.model.AddPolyline(self._doubles(coords))
        if closed:
            entity.Closed = True
        return self._style_entity(entity, color=color, layer=layer, lineweight=lineweight)

    def create_rect(
        self,
        corner1: PointLike,
        corner2: PointLike,
        *,
        color: int | None = None,
        layer: str | None = None,
        lineweight: int | None = None,
        **kwargs: Any,
    ) -> ComEntity:
        x1, y1, z1 = point_tuple(corner1)
        x2, y2, _ = point_tuple(corner2)
        return self.create_polyline(
            [(x1, y1, z1), (x2, y1, z1), (x2, y2, z1), (x1, y2, z1)],
            closed=True,
            color=color,
            layer=layer,
            lineweight=lineweight,
            **kwargs,
        )

    def create_text(
        self,
        position: PointLike,
        text: str,
        height: float,
        *,
        rotation_deg: float = 0.0,
        color: int | None = None,
        layer: str | None = None,
        **_: Any,
    ) -> ComEntity:
        entity = self.model.AddText(str(text), self._point(position), float(height))
        if rotation_deg:
            entity.Rotation = math.radians(float(rotation_deg))
        return self._style_entity(entity, color=color, layer=layer)

    def create_hatch(
        self,
        boundary: Sequence[Any],
        *,
        pattern_name: str = "SOLID",
        scale: float = 1.0,
        color: int | None = None,
        layer: str | None = None,
        **_: Any,
    ) -> ComEntity:
        if not boundary:
            raise ValueError("boundary cannot be empty")
        if _looks_like_points(boundary):
            boundary_entities = [self.create_polyline(boundary, closed=True, layer=layer).raw]
        else:
            boundary_entities = [_unwrap_entity(entity) for entity in boundary]
        hatch = self.model.AddHatch(0, pattern_name, True)
        hatch.AppendOuterLoop(self._dispatch_array(boundary_entities))
        hatch.PatternScale = float(scale)
        if hasattr(hatch, "Evaluate"):
            hatch.Evaluate()
        return self._style_entity(hatch, color=color, layer=layer)

    def create_dimension(
        self,
        pt1: PointLike,
        pt2: PointLike,
        dim_line_pt: PointLike,
        *,
        text: str | None = None,
        color: int | None = None,
        layer: str | None = None,
        rotation: float | None = None,
        **_: Any,
    ) -> ComEntity:
        entity = self.model.AddDimAligned(self._point(pt1), self._point(pt2), self._point(dim_line_pt))
        if text is not None:
            entity.TextOverride = str(text)
        if rotation is not None:
            entity.Rotation = float(rotation)
        return self._style_entity(entity, color=color, layer=layer)

    def create_table(self, position: PointLike, **kwargs: Any) -> Any:
        from .tables import create_table

        return create_table(self, position, **kwargs)

    def ensure_layer(self, name: str, *, color: int | None = None) -> Any:
        layers = self.document.layers
        for layer in _iter_com_collection(layers):
            if str(getattr(layer, "Name", "")).lower() == name.lower():
                self.doc.ActiveLayer = layer
                if color is not None:
                    layer.Color = int(color)
                return layer
        layer = layers.Add(name)
        if color is not None:
            layer.Color = int(color)
        self.doc.ActiveLayer = layer
        return layer

    def regen(self, mode: int = 1) -> None:
        self.document.regen(mode)

    def save_as(self, path: str) -> None:
        self.document.save_as(path)

    def zoom_extents(self) -> None:
        owner = getattr(self.document, "_owner", None)
        app = getattr(owner, "_app", None)
        if app is not None and hasattr(app, "ZoomExtents"):
            app.ZoomExtents()
            return
        viewport = getattr(self.doc, "ActiveViewport", None)
        if viewport is not None and hasattr(viewport, "ZoomExtents"):
            viewport.ZoomExtents()

    def _style_entity(
        self,
        entity: Any,
        *,
        color: int | None = None,
        layer: str | None = None,
        lineweight: int | None = None,
    ) -> ComEntity:
        if layer:
            self.ensure_layer(layer)
            entity.Layer = layer
        if color is not None:
            entity.Color = int(color)
        if lineweight is not None:
            entity.LineWeight = int(lineweight)
        return ComEntity(entity)

    def _point(self, point: PointLike) -> Any:
        return variant_point(point, com_client=self._com_client, pythoncom_module=self._pythoncom)

    def _doubles(self, values: Iterable[float]) -> Any:
        return variant_doubles(values, com_client=self._com_client, pythoncom_module=self._pythoncom)

    def _dispatch_array(self, values: Iterable[Any]) -> Any:
        return variant_dispatch_array(values, com_client=self._com_client, pythoncom_module=self._pythoncom)


def _unwrap_entity(value: Any) -> Any:
    return value.raw if hasattr(value, "raw") else value


def _looks_like_points(values: Sequence[Any]) -> bool:
    first = values[0]
    if hasattr(first, "x") and hasattr(first, "y"):
        return True
    return isinstance(first, (list, tuple)) and len(first) in (2, 3)


def _iter_com_collection(collection: Any) -> Iterable[Any]:
    count = int(getattr(collection, "Count", 0))
    for index in range(count):
        yield collection.Item(index)
