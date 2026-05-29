"""Pythonic CAD data helpers."""

from __future__ import annotations

import array
import math
import operator
from typing import Any, Iterable, Sequence, Tuple, Union

from ._com import variant_array

Number = Union[int, float]
PointLike = Union["Point2", "Vector2", Sequence[Number], Any]


class Point2(array.array):
    """2D point with an optional z coordinate for CAD COM calls.

    ``Point2`` accepts ``(x, y)``, ``(x, y, z)``, another point-like object
    with ``x``/``y``/``z`` attributes, or explicit ``x, y, z`` arguments.
    It supports simple vector arithmetic for script ergonomics.
    """

    _display_name = "Point2"

    def __new__(cls, x_or_seq: PointLike = 0.0, y: Number = 0.0, z: Number = 0.0):
        values = _coerce_point_tuple(x_or_seq, y, z)
        return super().__new__(cls, "d", values)

    @property
    def x(self) -> float:
        return float(self[0])

    @x.setter
    def x(self, value: Number) -> None:
        self[0] = float(value)

    @property
    def y(self) -> float:
        return float(self[1])

    @y.setter
    def y(self, value: Number) -> None:
        self[1] = float(value)

    @property
    def z(self) -> float:
        return float(self[2])

    @z.setter
    def z(self, value: Number) -> None:
        self[2] = float(value)

    def distance_to(self, other: PointLike) -> float:
        return distance(self, other)

    def __add__(self, other: Any) -> "Point2":
        return self._binary(other, operator.add)

    def __sub__(self, other: Any) -> "Point2":
        return self._binary(other, operator.sub)

    def __mul__(self, other: Any) -> "Point2":
        return self._binary(other, operator.mul)

    def __truediv__(self, other: Any) -> "Point2":
        return self._binary(other, operator.truediv)

    __radd__ = __add__
    __rmul__ = __mul__

    def __rsub__(self, other: Any) -> "Point2":
        return type(self)(other)._binary(self, operator.sub)

    def __rtruediv__(self, other: Any) -> "Point2":
        return type(self)(other)._binary(self, operator.truediv)

    def __neg__(self) -> "Point2":
        return type(self)(-self.x, -self.y, -self.z)

    def __iadd__(self, other: Any) -> "Point2":
        return self._inplace(other, operator.add)

    def __isub__(self, other: Any) -> "Point2":
        return self._inplace(other, operator.sub)

    def __imul__(self, other: Any) -> "Point2":
        return self._inplace(other, operator.mul)

    def __itruediv__(self, other: Any) -> "Point2":
        return self._inplace(other, operator.truediv)

    def _binary(self, other: Any, op: Any) -> "Point2":
        if isinstance(other, (int, float)):
            return type(self)(op(self.x, other), op(self.y, other), op(self.z, other))
        point = Point2(other)
        return type(self)(op(self.x, point.x), op(self.y, point.y), op(self.z, point.z))

    def _inplace(self, other: Any, op: Any) -> "Point2":
        result = self._binary(other, op)
        self.x, self.y, self.z = result.x, result.y, result.z
        return self

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return f"{self._display_name}({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, (array.array, list, tuple, Point2)) and not (
            hasattr(other, "x") and hasattr(other, "y")
        ):
            return False
        try:
            return tuple(self) == point_tuple(other)
        except Exception:
            return False


class Vector2(Point2):
    """2D vector with an optional z coordinate for CAD COM calls."""

    _display_name = "Vector2"


def _coerce_point_tuple(x_or_seq: PointLike, y: Number = 0.0, z: Number = 0.0) -> Tuple[float, float, float]:
    if isinstance(x_or_seq, Point2):
        return (x_or_seq.x, x_or_seq.y, x_or_seq.z)
    if hasattr(x_or_seq, "x") and hasattr(x_or_seq, "y"):
        return (
            float(x_or_seq.x),
            float(x_or_seq.y),
            float(getattr(x_or_seq, "z", 0.0)),
        )
    if isinstance(x_or_seq, (array.array, list, tuple)):
        if len(x_or_seq) == 2:
            return (float(x_or_seq[0]), float(x_or_seq[1]), 0.0)
        if len(x_or_seq) == 3:
            return (float(x_or_seq[0]), float(x_or_seq[1]), float(x_or_seq[2]))
        raise ValueError("Point sequences must contain 2 or 3 values")
    return (float(x_or_seq), float(y), float(z))


def point_tuple(point: PointLike) -> Tuple[float, float, float]:
    """Return a plain ``(x, y, z)`` tuple."""
    return tuple(Point2(point))  # type: ignore[return-value]


def distance(p1: PointLike, p2: PointLike) -> float:
    """Return Euclidean distance between two 3D points."""
    left = Point2(p1)
    right = Point2(p2)
    return math.sqrt(
        (left.x - right.x) ** 2 + (left.y - right.y) ** 2 + (left.z - right.z) ** 2
    )


def variant_point(
    point: PointLike,
    *,
    com_client: Any | None = None,
    pythoncom_module: Any | None = None,
) -> Any:
    """Return a COM ``VT_ARRAY | VT_R8`` point."""
    pythoncom_module = pythoncom_module or _load_pythoncom_from_client(com_client)
    return variant_array(
        Point2(point),
        pythoncom_module.VT_R8,
        com_client=com_client,
        pythoncom_module=pythoncom_module,
    )


def variant_doubles(
    values: Iterable[Number],
    *,
    com_client: Any | None = None,
    pythoncom_module: Any | None = None,
) -> Any:
    """Return a COM ``VT_ARRAY | VT_R8`` double array."""
    pythoncom_module = pythoncom_module or _load_pythoncom_from_client(com_client)
    return variant_array(
        [float(v) for v in values],
        pythoncom_module.VT_R8,
        com_client=com_client,
        pythoncom_module=pythoncom_module,
    )


def variant_dispatch_array(
    values: Iterable[Any],
    *,
    com_client: Any | None = None,
    pythoncom_module: Any | None = None,
) -> Any:
    """Return a COM ``VT_ARRAY | VT_DISPATCH`` array."""
    pythoncom_module = pythoncom_module or _load_pythoncom_from_client(com_client)
    return variant_array(
        values,
        pythoncom_module.VT_DISPATCH,
        com_client=com_client,
        pythoncom_module=pythoncom_module,
    )


def double_array(*seq: Any) -> array.array:
    """Return an array of doubles for COM APIs."""
    return _sequence_to_array("d", *seq)


def int_array(*seq: Any) -> array.array:
    """Return an array of signed ints for COM APIs."""
    return _sequence_to_array("l", *seq)


def short_array(*seq: Any) -> array.array:
    """Return an array of signed shorts for COM APIs."""
    return _sequence_to_array("h", *seq)


def _sequence_to_array(typecode: str, *sequence: Any) -> array.array:
    if len(sequence) == 1 and isinstance(sequence[0], (array.array, list, tuple)):
        return array.array(typecode, sequence[0])
    return array.array(typecode, sequence)


def _load_pythoncom_from_client(com_client: Any | None) -> Any:
    if com_client is not None and hasattr(com_client, "_pythoncom"):
        return com_client._pythoncom
    from ._com import load_pywin32

    return load_pywin32()[1]
