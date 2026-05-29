"""Exceptions raised by pygcadwin."""


class PyGcadWinError(RuntimeError):
    """Base exception for pygcadwin errors."""


class PyGcadWinImportError(PyGcadWinError):
    """Raised when pywin32 is required but unavailable."""


class CadConnectionError(PyGcadWinError):
    """Raised when GstarCAD cannot be connected or started."""


class CadDocumentError(PyGcadWinError):
    """Raised when a valid GstarCAD document cannot be obtained."""


class ToolDispatchError(PyGcadWinError):
    """Raised for invalid agent tool dispatch requests."""

