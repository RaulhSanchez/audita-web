"""Servicio de backup automático de bases de datos SQLite y ChromaDB."""
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path


class BackupService:
    def __init__(self):
        self.db_dir = Path("./db")
        self.backup_dir = Path("./backups")

    def create_backup(self, triggered_by="system") -> tuple[bool, str]:
        """
        Crea un ZIP con toda la carpeta ./db/ (SQLite + ChromaDB).
        Returns (success, message_or_path).
        """
        try:
            self.backup_dir.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_name = f"cortexa_backup_{ts}.zip"
            zip_path = self.backup_dir / zip_name

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                for root, dirs, files in os.walk(self.db_dir):
                    # Skip .git and __pycache__
                    dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
                    for file in files:
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(self.db_dir.parent)
                        zf.write(full_path, arcname)

            size_mb = zip_path.stat().st_size / (1024 * 1024)
            self.cleanup_old_backups(keep=10)
            return True, str(zip_path)
        except Exception as e:
            return False, str(e)

    def list_backups(self) -> list[dict]:
        """Devuelve lista de backups ordenada por fecha (más reciente primero)."""
        if not self.backup_dir.exists():
            return []
        backups = []
        for f in sorted(self.backup_dir.glob("cortexa_backup_*.zip"), reverse=True):
            stat = f.stat()
            backups.append({
                "filename": f.name,
                "path": str(f),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
            })
        return backups

    def cleanup_old_backups(self, keep=10):
        """Elimina backups más antiguos, conservando los últimos `keep`."""
        if not self.backup_dir.exists():
            return
        all_bk = sorted(self.backup_dir.glob("cortexa_backup_*.zip"), reverse=True)
        for old in all_bk[keep:]:
            try:
                old.unlink()
            except Exception:
                pass

    def get_total_size_mb(self) -> float:
        if not self.backup_dir.exists():
            return 0.0
        total = sum(f.stat().st_size for f in self.backup_dir.glob("*.zip") if f.is_file())
        return round(total / (1024 * 1024), 1)


backup_service = BackupService()
