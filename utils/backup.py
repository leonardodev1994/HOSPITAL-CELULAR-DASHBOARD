import shutil
import subprocess
from datetime import datetime
from pathlib import Path


DB_PATH = Path("banco.db")
BACKUP_DIR = Path("backups")
LAST_BACKUP_FILE = BACKUP_DIR / ".last_auto_backup"
LAST_CLOUD_ERROR_FILE = BACKUP_DIR / ".last_cloud_error"
RCLONE_PATH = Path("tools/rclone")
GDRIVE_REMOTE = "gdrive:Hospital do Celular/Backups"


def ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_filename(prefix="backup"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_banco_{timestamp}.db"


def create_backup(prefix="manual"):
    ensure_backup_dir()

    if not DB_PATH.exists():
        raise FileNotFoundError("Banco de dados banco.db não encontrado.")

    destination = BACKUP_DIR / backup_filename(prefix)
    shutil.copy2(DB_PATH, destination)
    return destination


def list_backups():
    ensure_backup_dir()
    backups = sorted(
        BACKUP_DIR.glob("*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    return backups


def backup_info(path):
    stat = path.stat()
    return {
        "arquivo": path.name,
        "caminho": str(path),
        "tamanho_mb": stat.st_size / (1024 * 1024),
        "criado_em": datetime.fromtimestamp(stat.st_mtime),
    }


def latest_backup():
    backups = list_backups()
    return backups[0] if backups else None


def cleanup_old_backups(keep=30):
    backups = list_backups()

    for path in backups[keep:]:
        path.unlink(missing_ok=True)


def cloud_is_configured():
    if not RCLONE_PATH.exists():
        return False

    result = subprocess.run(
        [str(RCLONE_PATH), "listremotes"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0 and "gdrive:" in result.stdout


def upload_backup_to_drive(path):
    if not cloud_is_configured():
        raise RuntimeError("Google Drive não configurado no rclone.")

    result = subprocess.run(
        [str(RCLONE_PATH), "copy", str(path), GDRIVE_REMOTE],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "Falha ao enviar backup.")

    return True


def list_cloud_backups():
    if not cloud_is_configured():
        return []

    result = subprocess.run(
        [str(RCLONE_PATH), "ls", GDRIVE_REMOTE],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return []

    backups = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            backups.append({
                "tamanho": int(parts[0]),
                "arquivo": parts[1],
            })

    return backups


def run_daily_auto_backup():
    ensure_backup_dir()
    today = datetime.now().strftime("%Y-%m-%d")

    if LAST_BACKUP_FILE.exists() and LAST_BACKUP_FILE.read_text().strip() == today:
        return None

    backup_path = create_backup(prefix="auto")
    if cloud_is_configured():
        try:
            upload_backup_to_drive(backup_path)
            LAST_CLOUD_ERROR_FILE.unlink(missing_ok=True)
        except Exception as error:
            LAST_CLOUD_ERROR_FILE.write_text(str(error))

    LAST_BACKUP_FILE.write_text(today)
    cleanup_old_backups()
    return backup_path
