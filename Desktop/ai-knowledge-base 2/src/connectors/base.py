"""
src/connectors/base.py
Interfaz base y registro de conectores ETL.

Cada conector extiende BaseConnector e implementa:
  - test_connection() → (ok: bool, msg: str)
  - list_files()      → List[ConnectorFile]
  - fetch_file(file)  → bytes

El SyncService llama a estos métodos para indexar documentos
en ChromaDB usando el pipeline de ingest_service existente.

Configuración de cada conector se guarda en userdb:
  connector_<tipo>_<campo>  p.ej.  connector_gdrive_folder_id
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


# ─── Modelo de fichero devuelto por cada conector ───────────────────────────

@dataclass
class ConnectorFile:
    file_id:      str            # ID único en el origen (no cambia al renombrar)
    name:         str            # Nombre del fichero con extensión
    modified_at:  datetime       # Última modificación en el origen
    size_bytes:   int = 0
    mime_type:    str = ""
    url:          str = ""       # URL de acceso directo (para auditoría)
    extra:        Dict[str, Any] = field(default_factory=dict)


# ─── Resultado de sincronización ────────────────────────────────────────────

@dataclass
class SyncResult:
    connector:   str
    started_at:  datetime
    finished_at: datetime
    added:       int = 0         # Ficheros nuevos indexados
    updated:     int = 0         # Ficheros actualizados
    skipped:     int = 0         # Sin cambios
    errors:      int = 0
    messages:    List[str] = field(default_factory=list)

    @property
    def total(self):
        return self.added + self.updated + self.skipped + self.errors

    def summary(self) -> str:
        dur = (self.finished_at - self.started_at).seconds
        return (f"[{self.connector}] +{self.added} upd:{self.updated} "
                f"skip:{self.skipped} err:{self.errors} ({dur}s)")


# ─── Interfaz base ──────────────────────────────────────────────────────────

class BaseConnector(ABC):
    """
    Clase base para todos los conectores ETL.
    Subclases deben implementar test_connection, list_files y fetch_file.
    """

    # Identificador único del tipo (e.g. "gdrive", "sharepoint", "confluence")
    connector_type: str = ""

    # Nombre legible
    display_name: str = ""

    # Extensiones soportadas (vacío = todas)
    supported_extensions: List[str] = []

    def __init__(self):
        self._settings_cache: Dict[str, str] = {}

    def _setting(self, key: str, default: str = "") -> str:
        """Lee configuración desde userdb con prefijo connector_<tipo>_."""
        from src.core.userdb import userdb
        full_key = f"connector_{self.connector_type}_{key}"
        return userdb.get_setting(full_key, default) or default

    def save_setting(self, key: str, value: str, updated_by: str = "system") -> None:
        from src.core.userdb import userdb
        full_key = f"connector_{self.connector_type}_{key}"
        userdb.set_setting(full_key, value, updated_by=updated_by)

    def is_configured(self) -> bool:
        """Devuelve True si el conector tiene la configuración mínima."""
        return False   # subclases deben sobreescribir

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Comprueba que las credenciales son correctas y el origen es accesible."""
        ...

    @abstractmethod
    def list_files(self) -> List[ConnectorFile]:
        """Lista todos los ficheros disponibles en el origen."""
        ...

    @abstractmethod
    def fetch_file(self, file: ConnectorFile) -> bytes:
        """Descarga el contenido de un fichero."""
        ...

    def extension_allowed(self, name: str) -> bool:
        if not self.supported_extensions:
            return True
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        return ext in self.supported_extensions


# ─── Registro global de conectores ─────────────────────────────────────────

_REGISTRY: Dict[str, type] = {}


def register(cls: type) -> type:
    """Decorador para registrar un conector."""
    _REGISTRY[cls.connector_type] = cls
    return cls


def get_connector(connector_type: str) -> Optional[BaseConnector]:
    """Devuelve una instancia del conector pedido, o None si no existe."""
    cls = _REGISTRY.get(connector_type)
    return cls() if cls else None


def all_connectors() -> List[BaseConnector]:
    """Devuelve instancias de todos los conectores registrados."""
    return [cls() for cls in _REGISTRY.values()]
