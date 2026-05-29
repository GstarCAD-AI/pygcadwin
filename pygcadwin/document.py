"""Document wrapper for GstarCAD COM automation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .exceptions import CadDocumentError


class Document:
    """Lightweight wrapper around a GstarCAD COM document."""

    def __init__(self, raw: Any, owner: Any | None = None):
        if raw is None:
            raise CadDocumentError("Cannot wrap a null GstarCAD document")
        self.raw = raw
        self._owner = owner

    @classmethod
    def current(cls, *, create_if_missing: bool = True, visible: bool = True) -> "Document":
        from .api import Gcad

        return Gcad(create_if_missing=create_if_missing, visible=visible).document

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        create_if_missing: bool = True,
        visible: bool = True,
    ) -> "Document":
        from .api import Gcad

        cad = Gcad(create_if_missing=create_if_missing, visible=visible)
        opened = cad.app.Documents.Open(str(path))
        cad._document = cls(opened, owner=cad)
        return cad._document

    @property
    def name(self) -> str:
        return str(getattr(self.raw, "Name", ""))

    @property
    def model_space(self) -> Any:
        return self.raw.ModelSpace

    @property
    def layers(self) -> Any:
        return self.raw.Layers

    @property
    def layouts(self) -> Any:
        return self.raw.Layouts

    @property
    def active_layout(self) -> Any:
        return self.raw.ActiveLayout

    def open_related(self, path: str | Path) -> "Document":
        if self._owner is None:
            raise CadDocumentError("Opening a document requires an owning Gcad instance")
        opened = self._owner.app.Documents.Open(str(path))
        return Document(opened, owner=self._owner)

    def save_as(self, path: str | Path) -> None:
        path = Path(path)
        if path.parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        self.raw.SaveAs(str(path))

    def regen(self, mode: int = 1) -> None:
        self.raw.Regen(mode)

    def close(self, save_changes: bool = False) -> None:
        self.raw.Close(bool(save_changes))

    def iter_layouts(self, *, skip_model: bool = True):
        from .layouts import iter_layouts

        return iter_layouts(self, skip_model=skip_model)
