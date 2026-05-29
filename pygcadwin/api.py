"""Main GstarCAD COM automation object."""

from __future__ import annotations

import time
from typing import Any, Callable

from ._com import GSTARCAD_PROGID, gstarcad_prog_id_candidates, load_pywin32
from .document import Document
from .exceptions import CadConnectionError, CadDocumentError


class Gcad:
    """Connect to or start GstarCAD through a registered COM ProgID."""

    def __init__(
        self,
        create_if_missing: bool | None = True,
        visible: bool = True,
        startup_wait: float = 20.0,
        *,
        create_if_not_exists: bool | None = None,
        prog_id: str = GSTARCAD_PROGID,
        com_client: Any | None = None,
        pythoncom_module: Any | None = None,
        sleep: Callable[[float], None] | None = None,
    ):
        if create_if_not_exists is not None:
            create_if_missing = create_if_not_exists
        self.create_if_missing = create_if_missing
        self.visible = visible
        self.startup_wait = startup_wait
        self.prog_id = prog_id
        self._prog_ids = gstarcad_prog_id_candidates(prog_id)
        self._com_client = com_client
        self._pythoncom = pythoncom_module
        if self._com_client is not None and self._pythoncom is not None:
            setattr(self._com_client, "_pythoncom", self._pythoncom)
        self._sleep = sleep or time.sleep
        self._app: Any | None = None
        self._document: Document | None = None
        self._coinitialized = False

    def __enter__(self) -> "Gcad":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    @property
    def app(self) -> Any:
        return self.connect()

    Application = app

    @property
    def doc(self) -> Any:
        return self.document.raw

    ActiveDocument = doc

    @property
    def document(self) -> Document:
        self.connect()
        if self._document is None:
            self._document = Document(self._ensure_document(), owner=self)
        return self._document

    @property
    def model(self) -> Any:
        return self.document.model_space

    @property
    def context(self) -> Any:
        from .context import Context

        return Context(self.document)

    def iter_layouts(self, doc: Any | None = None, skip_model: bool = True):
        from .layouts import iter_layouts

        return iter_layouts(doc or self.doc, skip_model=skip_model)

    def iter_objects(
        self,
        object_name_or_list: str | list[str] | None = None,
        block: Any | None = None,
        limit: int | None = None,
        dont_cast: bool = False,
    ):
        from .selection import iter_objects

        return iter_objects(
            self.doc,
            object_name_or_list,
            block=block,
            limit=limit,
            dont_cast=dont_cast,
            best_interface=self.best_interface,
        )

    def iter_objects_fast(
        self,
        object_name_or_list: str | list[str] | None = None,
        container: Any | None = None,
        limit: int | None = None,
    ):
        return self.iter_objects(object_name_or_list, container, limit, dont_cast=True)

    def find_one(
        self,
        object_name_or_list: str | list[str],
        container: Any | None = None,
        predicate: Callable[[Any], bool] | None = None,
    ) -> Any | None:
        from .selection import find_one

        return find_one(
            self.doc,
            object_name_or_list,
            block=container,
            predicate=predicate,
            best_interface=self.best_interface,
        )

    def best_interface(self, obj: Any) -> Any:
        """Return the best available Python interface for a COM object.

        pywin32 dynamic dispatch usually already exposes usable objects. When
        a test/client injects a COM client with ``GetBestInterface`` this
        delegates; otherwise the original object is returned.
        """
        getter = getattr(self.com_client, "GetBestInterface", None)
        return getter(obj) if getter is not None else obj

    def prompt(self, text: str) -> None:
        print(text)
        self.doc.Utility.Prompt(f"{text}\n")

    def get_selection(self, text: str = "Select objects") -> Any:
        from .selection import get_selection

        self.prompt(text)
        return get_selection(self.doc, name="SS1")

    @property
    def com_client(self) -> Any:
        self._load_com()
        return self._com_client

    @property
    def pythoncom(self) -> Any:
        self._load_com()
        return self._pythoncom

    def connect(self) -> Any:
        """Return the active app, starting GstarCAD when configured to do so."""
        self._connect_app()
        if self._document is None:
            self._document = Document(self._ensure_document(), owner=self)
        return self._app

    def new_document(self) -> Document:
        """Create a new drawing document and make it current for this wrapper."""
        self._connect_app()
        if self._app is None:
            raise CadConnectionError("GstarCAD application is not connected")
        try:
            raw_document = self._app.Documents.Add()
        except Exception as exc:
            raise CadDocumentError("Failed to create a new GstarCAD document") from exc
        self._document = Document(raw_document, owner=self)
        return self._document

    def _connect_app(self) -> Any:
        """Return the active app, starting GstarCAD without selecting a document.

        ``visible`` and ``startup_wait`` only apply when this call has to launch
        a fresh GstarCAD process via ``Dispatch``. When ``GetActiveObject`` finds
        an already-running session, the existing window's visibility is left
        alone so we don't disrupt a live user session.
        """
        if self._app is not None:
            return self._app
        self._load_com()
        self._coinitialize()

        try:
            assert self._com_client is not None
            active_exc = None
            for prog_id in self._prog_ids:
                try:
                    self._app = self._com_client.GetActiveObject(prog_id)
                    self.prog_id = prog_id
                    break
                except Exception as exc:
                    active_exc = exc

            if self._app is None:
                if not self.create_if_missing:
                    raise CadConnectionError(
                        "No active GstarCAD COM server found for "
                        f"{', '.join(self._prog_ids)}"
                    ) from active_exc

                dispatch_exc = None
                for prog_id in self._prog_ids:
                    try:
                        self._app = self._com_client.Dispatch(prog_id)
                        self.prog_id = prog_id
                        break
                    except Exception as exc:
                        dispatch_exc = exc
                if self._app is None:
                    raise CadConnectionError(
                        "Failed to start GstarCAD COM server. Tried ProgIDs: "
                        f"{', '.join(self._prog_ids)}"
                    ) from dispatch_exc

                self._app.Visible = self.visible
                if self.startup_wait > 0:
                    self._sleep(self.startup_wait)

            return self._app
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Release wrapper references and uninitialize COM for this thread."""
        self._document = None
        self._app = None
        if self._coinitialized and self._pythoncom is not None:
            try:
                self._pythoncom.CoUninitialize()
            finally:
                self._coinitialized = False

    def _load_com(self) -> None:
        if self._com_client is not None and self._pythoncom is not None:
            setattr(self._com_client, "_pythoncom", self._pythoncom)
            return
        self._com_client, self._pythoncom = load_pywin32()
        setattr(self._com_client, "_pythoncom", self._pythoncom)

    def _coinitialize(self) -> None:
        if self._coinitialized:
            return
        assert self._pythoncom is not None
        self._pythoncom.CoInitialize()
        self._coinitialized = True

    def _ensure_document(self) -> Any:
        if self._app is None:
            raise CadConnectionError("GstarCAD application is not connected")
        try:
            docs = self._app.Documents
            if getattr(docs, "Count", 0) == 0:
                return docs.Add()
            return self._app.ActiveDocument
        except Exception as exc:
            try:
                return self._app.Documents.Add()
            except Exception as add_exc:
                raise CadDocumentError("Failed to obtain or create a GstarCAD document") from add_exc

    from .types import (
        double_array as _double_array,
        int_array as _int_array,
        short_array as _short_array,
    )

    double_array = staticmethod(_double_array)
    int_array = staticmethod(_int_array)
    short_array = staticmethod(_short_array)


Autocad = Gcad
ACAD = None
