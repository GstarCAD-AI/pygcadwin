"""Pythonic COM automation API for GstarCAD on Windows."""

from .api import ACAD, Autocad, Gcad
from .cache import Cached
from .context import ComEntity, Context
from .document import Document
from .drawings import FlangeSpec, draw_flange
from .exceptions import (
    CadConnectionError,
    CadDocumentError,
    PyGcadWinError,
    PyGcadWinImportError,
    ToolDispatchError,
)
from .layouts import (
    get_model_space,
    get_paper_space,
    iter_layout_entities,
    iter_layouts,
)
from .selection import (
    create_selection_set,
    delete_selection_set,
    find_one,
    get_selection,
    iter_objects,
    select_filter,
    select_predicate,
)
from .tables import (
    FormatNotSupported,
    Table,
    available_read_formats,
    available_write_formats,
    create_table,
    get_cell_text,
    mtext_to_string,
    set_cell_text,
    string_to_mtext,
    suppress_regeneration,
    text_width,
    unformat_mtext,
)
from .tools import execute_tool, run_actions, tool_schemas
from .types import (
    PointLike,
    Point2,
    Vector2,
    distance,
    double_array,
    int_array,
    point_tuple,
    short_array,
    variant_dispatch_array,
    variant_doubles,
    variant_point,
)
from .utils import dynamic_print, suppressed_regeneration_of, timing
from .view import Snapshot, View

__version__ = "0.1.0"

__all__ = [
    "ACAD",
    "Autocad",
    "CadConnectionError",
    "CadDocumentError",
    "Cached",
    "ComEntity",
    "Context",
    "Document",
    "FormatNotSupported",
    "FlangeSpec",
    "Gcad",
    "PointLike",
    "Point2",
    "PyGcadWinError",
    "PyGcadWinImportError",
    "ToolDispatchError",
    "Table",
    "Vector2",
    "Snapshot",
    "View",
    "__version__",
    "available_read_formats",
    "available_write_formats",
    "distance",
    "draw_flange",
    "create_table",
    "create_selection_set",
    "delete_selection_set",
    "double_array",
    "dynamic_print",
    "execute_tool",
    "find_one",
    "get_cell_text",
    "get_model_space",
    "get_paper_space",
    "get_selection",
    "int_array",
    "iter_layout_entities",
    "iter_layouts",
    "iter_objects",
    "mtext_to_string",
    "point_tuple",
    "run_actions",
    "select_filter",
    "select_predicate",
    "set_cell_text",
    "short_array",
    "string_to_mtext",
    "suppress_regeneration",
    "suppressed_regeneration_of",
    "text_width",
    "timing",
    "tool_schemas",
    "unformat_mtext",
    "variant_dispatch_array",
    "variant_doubles",
    "variant_point",
]
