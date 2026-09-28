"""Celery-задачі для core: автоматичне резервне копіювання БД."""
import logging

from celery import shared_task

from .backup import create_backup, rotate_backups

logger = logging.getLogger(__name__)


@shared_task(name='core.tasks.auto_backup_database')
def auto_backup_database():
    """Створює новий JSON-бекап БД і чистить старі (rolling window).

    Викликається за розкладом Celery Beat (див. `celery_app.py`).
    Кількість файлів, що зберігаються — settings.BACKUP_KEEP_COUNT (default 30).
    """
    try:
        info = create_backup()
        logger.info(f"Auto-backup created: {info['filename']} ({info['size']} bytes)")
    except Exception as e:
        logger.exception(f'Auto-backup failed: {e}')
        raise

    try:
        deleted = rotate_backups()
        if deleted:
            logger.info(f'Rotation removed {len(deleted)} old backups: {deleted}')
    except Exception as e:
        # Ротація не критична — не валимо задачу, якщо створення пройшло успішно
        logger.exception(f'Backup rotation failed (non-critical): {e}')

    return {'created': info['filename'], 'size': info['size']}
