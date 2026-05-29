"""Reusable mechanical drawing helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .context import ComEntity, Context


@dataclass(frozen=True)
class FlangeSpec:
    """Nominal flange dimensions in drawing units."""

    outer_diameter: float = 200.0
    bore_diameter: float = 80.0
    bolt_circle_diameter: float = 150.0
    bolt_hole_diameter: float = 18.0
    bolt_count: int = 8
    thickness: float = 24.0
    hub_diameter: float = 110.0
    hub_height: float = 35.0
    title: str = "FLANGE / 法兰"

    def validate(self) -> None:
        if self.outer_diameter <= 0:
            raise ValueError("outer_diameter must be positive")
        if self.bore_diameter <= 0:
            raise ValueError("bore_diameter must be positive")
        if self.bolt_circle_diameter <= 0:
            raise ValueError("bolt_circle_diameter must be positive")
        if self.bolt_hole_diameter <= 0:
            raise ValueError("bolt_hole_diameter must be positive")
        if self.bolt_count < 2:
            raise ValueError("bolt_count must be at least 2")
        if self.thickness <= 0:
            raise ValueError("thickness must be positive")
        if self.hub_diameter < self.bore_diameter:
            raise ValueError("hub_diameter must be greater than or equal to bore_diameter")
        if self.hub_diameter > self.outer_diameter:
            raise ValueError("hub_diameter must be smaller than or equal to outer_diameter")
        if self.bore_diameter >= self.outer_diameter:
            raise ValueError("bore_diameter must be smaller than outer_diameter")
        if self.bolt_circle_diameter >= self.outer_diameter:
            raise ValueError("bolt_circle_diameter must be smaller than outer_diameter")
        if self.bolt_hole_diameter >= self.bore_diameter:
            raise ValueError("bolt_hole_diameter must be smaller than bore_diameter")
        if self.bolt_circle_diameter + self.bolt_hole_diameter >= self.outer_diameter:
            raise ValueError("bolt holes must fit inside outer_diameter")
        if self.bolt_circle_diameter - self.bolt_hole_diameter <= self.bore_diameter:
            raise ValueError("bolt holes must clear bore_diameter")


def draw_flange(
    context: Context,
    spec: FlangeSpec | None = None,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
    save_as: str | None = None,
) -> list[Any]:
    """Draw a flange top view, section view, dimensions, and parameter table."""

    spec = spec or FlangeSpec()
    spec.validate()

    entities: list[Any] = []
    _ensure_flange_layers(context)
    entities.extend(_draw_top_view(context, spec, origin))
    entities.extend(
        _draw_section_view(context, spec, (origin[0] + spec.outer_diameter * 1.7, origin[1]))
    )
    entities.extend(
        _draw_parameter_table(
            context,
            spec,
            (origin[0] - spec.outer_diameter / 2, origin[1] - spec.outer_diameter),
        )
    )
    context.create_text(
        (origin[0] - spec.outer_diameter / 2, origin[1] + spec.outer_diameter / 2 + 28),
        f"{spec.title} - TOP VIEW AND SECTION",
        7.0,
        layer="A-TEXT",
        color=4,
    )
    context.regen()
    context.zoom_extents()
    if save_as:
        context.save_as(save_as)
    return entities


def _ensure_flange_layers(context: Context) -> None:
    for name, color in (
        ("A-PART", 7),
        ("A-HOLE", 1),
        ("A-CENTER", 3),
        ("A-DIM", 2),
        ("A-HATCH", 8),
        ("A-TEXT", 4),
    ):
        context.ensure_layer(name, color=color)


def _draw_top_view(
    context: Context,
    spec: FlangeSpec,
    origin: tuple[float, float],
) -> list[ComEntity]:
    cx, cy = origin
    outer_radius = spec.outer_diameter / 2
    bore_radius = spec.bore_diameter / 2
    bolt_circle_radius = spec.bolt_circle_diameter / 2
    hole_radius = spec.bolt_hole_diameter / 2
    entities: list[ComEntity] = []

    entities.append(
        context.create_circle(origin, outer_radius, layer="A-PART", color=7, lineweight=30)
    )
    entities.append(
        context.create_circle(origin, bore_radius, layer="A-HOLE", color=1, lineweight=25)
    )
    entities.append(context.create_circle(origin, bolt_circle_radius, layer="A-CENTER", color=3))
    _set_linetype(entities[-1], "CENTER")

    center_extent = outer_radius + 16
    entities.append(
        context.create_segment(
            (cx - center_extent, cy),
            (cx + center_extent, cy),
            layer="A-CENTER",
            color=3,
        )
    )
    entities.append(
        context.create_segment(
            (cx, cy - center_extent),
            (cx, cy + center_extent),
            layer="A-CENTER",
            color=3,
        )
    )
    _set_linetype(entities[-1], "CENTER")
    _set_linetype(entities[-2], "CENTER")

    for index in range(spec.bolt_count):
        angle = math.tau * index / spec.bolt_count
        hole_center = (
            cx + bolt_circle_radius * math.cos(angle),
            cy + bolt_circle_radius * math.sin(angle),
        )
        entities.append(context.create_circle(hole_center, hole_radius, layer="A-HOLE", color=1))
        entities.append(
            context.create_segment(
                (hole_center[0] - hole_radius * 1.4, hole_center[1]),
                (hole_center[0] + hole_radius * 1.4, hole_center[1]),
                layer="A-CENTER",
                color=3,
            )
        )
        entities.append(
            context.create_segment(
                (hole_center[0], hole_center[1] - hole_radius * 1.4),
                (hole_center[0], hole_center[1] + hole_radius * 1.4),
                layer="A-CENTER",
                color=3,
            )
        )

    dim_y = cy - outer_radius - 28
    entities.append(
        context.create_dimension(
            (cx - outer_radius, dim_y),
            (cx + outer_radius, dim_y),
            (cx, dim_y - 14),
            text=f"OD {spec.outer_diameter:g}",
            layer="A-DIM",
            color=2,
        )
    )
    entities.append(
        context.create_dimension(
            (cx - bore_radius, cy + outer_radius + 18),
            (cx + bore_radius, cy + outer_radius + 18),
            (cx, cy + outer_radius + 32),
            text=f"BORE {spec.bore_diameter:g}",
            layer="A-DIM",
            color=2,
        )
    )
    context.create_text(
        (cx + outer_radius + 18, cy + 8),
        (
            f"{spec.bolt_count} x HOLE {spec.bolt_hole_diameter:g} "
            f"ON PCD {spec.bolt_circle_diameter:g}"
        ),
        4.5,
        layer="A-TEXT",
        color=4,
    )
    return entities


def _draw_section_view(
    context: Context,
    spec: FlangeSpec,
    origin: tuple[float, float],
) -> list[ComEntity]:
    cx, cy = origin
    outer_radius = spec.outer_diameter / 2
    bore_radius = spec.bore_diameter / 2
    hub_radius = spec.hub_diameter / 2
    bottom = cy - spec.thickness / 2
    top = cy + spec.thickness / 2
    hub_top = top + spec.hub_height
    entities: list[ComEntity] = []

    entities.append(
        context.create_rect(
            (cx - outer_radius, bottom),
            (cx + outer_radius, top),
            layer="A-PART",
            color=7,
            lineweight=30,
        )
    )
    entities.append(
        context.create_rect(
            (cx - hub_radius, top),
            (cx + hub_radius, hub_top),
            layer="A-PART",
            color=7,
            lineweight=30,
        )
    )
    entities.append(
        context.create_rect(
            (cx - bore_radius, bottom - 2),
            (cx + bore_radius, hub_top + 2),
            layer="A-HOLE",
            color=1,
        )
    )
    entities.append(
        context.create_segment(
            (cx, bottom - 16),
            (cx, hub_top + 16),
            layer="A-CENTER",
            color=3,
        )
    )
    _set_linetype(entities[-1], "CENTER")

    entities.extend(
        _draw_hatch_band(context, cx - outer_radius, cx - bore_radius, bottom, top, 8.0)
    )
    entities.extend(
        _draw_hatch_band(context, cx + bore_radius, cx + outer_radius, bottom, top, 8.0)
    )
    entities.extend(_draw_hatch_band(context, cx - hub_radius, cx - bore_radius, top, hub_top, 8.0))
    entities.extend(_draw_hatch_band(context, cx + bore_radius, cx + hub_radius, top, hub_top, 8.0))

    dim_x = cx + outer_radius + 28
    entities.append(
        context.create_dimension(
            (dim_x, bottom),
            (dim_x, top),
            (dim_x + 14, cy),
            text=f"THK {spec.thickness:g}",
            layer="A-DIM",
            color=2,
        )
    )
    entities.append(
        context.create_dimension(
            (cx - hub_radius, hub_top + 18),
            (cx + hub_radius, hub_top + 18),
            (cx, hub_top + 32),
            text=f"HUB {spec.hub_diameter:g}",
            layer="A-DIM",
            color=2,
        )
    )
    context.create_text(
        (cx - outer_radius, hub_top + 45),
        "SECTION A-A",
        5.0,
        layer="A-TEXT",
        color=4,
    )
    return entities


def _draw_hatch_band(
    context: Context,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    spacing: float,
) -> list[ComEntity]:
    if x_max <= x_min or y_max <= y_min:
        return []
    entities: list[ComEntity] = []
    height = y_max - y_min
    x = x_min - height
    while x < x_max:
        start_x = max(x, x_min)
        start_y = y_min + max(0.0, x_min - x)
        end_x = min(x + height, x_max)
        end_y = y_min + (end_x - x)
        if end_x > start_x:
            entities.append(
                context.create_segment(
                    (start_x, start_y),
                    (end_x, min(end_y, y_max)),
                    layer="A-HATCH",
                    color=8,
                )
            )
        x += spacing
    return entities


def _draw_parameter_table(
    context: Context,
    spec: FlangeSpec,
    position: tuple[float, float],
) -> list[Any]:
    table = context.create_table(
        position,
        data=[
            ["Parameter", "Value"],
            ["Outer diameter", f"{spec.outer_diameter:g}"],
            ["Bore diameter", f"{spec.bore_diameter:g}"],
            ["Bolt circle", f"{spec.bolt_circle_diameter:g}"],
            ["Bolt holes", f"{spec.bolt_count} x {spec.bolt_hole_diameter:g}"],
            ["Thickness", f"{spec.thickness:g}"],
            ["Hub", f"{spec.hub_diameter:g} x {spec.hub_height:g}"],
        ],
        title=spec.title,
        row_height=8.0,
        col_width=44.0,
        text_height=3.2,
        layer="A-TEXT",
    )
    return [table]


def _set_linetype(entity: ComEntity, value: str) -> None:
    try:
        entity.raw.Linetype = value
    except Exception:
        pass
