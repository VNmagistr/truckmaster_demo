"""Сервіс створення JSON-бекапів БД та їх ротації.

Єдина точка істини — використовується і REST-endpoint (`POST /api/backups/`),
і Celery-таск щоденного автобекапу.
"""
import io
import logging
import os
from datetime import datetime

from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)

# Файли, які виключаємо з dumpdata (стан ОС / генеровані Django)
EXCLUDED_MODELS = (
    'contenttypes',
    'auth.permission',
    'admin.logentry',
    'sessions.session',
)


def get_backup_dir():
    backup_dir = getattr(settings, 'BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def list_backup_files():
    """Повертає відсортований (найновіші перші) список повних шляхів до backup_*.json."""
    backup_dir = get_backup_dir()
    files = [
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.startswith('backup_') and f.endswith('.json')
    ]
    files.sort(reverse=True)
    return files


def backup_info(filepath):
    stat = os.stat(filepath)
    return {
        'filename': os.path.basename(filepath),
        'size': stat.st_size,
        'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def create_backup():
    """Створює новий JSON-бекап з `dumpdata`. Повертає dict з info."""
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'backup_{timestamp}.json'
    filepath = os.path.join(backup_dir, filename)

    buf = io.StringIO()
    call_command(
        'dumpdata',
        '--natural-foreign',
        '--natural-primary',
        *[f'--exclude={m}' for m in EXCLUDED_MODELS],
        '--indent=2',
        stdout=buf,
    )
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(buf.getvalue())

    logger.info(f'Backup created: {filename} ({os.path.getsize(filepath)} bytes)')
    return backup_info(filepath)


def rotate_backups(keep=None):
    """Видаляє старі бекапи, залишаючи останні `keep` штук.

    За замовчуванням — `settings.BACKUP_KEEP_COUNT` або 30.
    Повертає список видалених імен файлів.
    """
    if keep is None:
        keep = getattr(settings, 'BACKUP_KEEP_COUNT', 30)
    files = list_backup_files()
    if len(files) <= keep:
        return []
    to_delete = files[keep:]
    deleted = []
    for path in to_delete:
        try:
            os.remove(path)
            deleted.append(os.path.basename(path))
        except OSError as e:
            logger.warning(f'Failed to delete old backup {path}: {e}')
    if deleted:
        logger.info(f'Rotated backups: removed {len(deleted)} old files (kept {keep})')
    return deleted
