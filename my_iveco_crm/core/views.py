# core/views.py

import io
import os
import json
from datetime import datetime

from django.conf import settings
from django.core.management import call_command
from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Module
from .serializers import ModuleSerializer


class ModuleListView(APIView):
    """
    GET  /api/modules/  — список усіх модулів (тільки адміністратор).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modules = Module.objects.all()
        return Response(ModuleSerializer(modules, many=True).data)


class EnumsView(APIView):
    """
    GET /api/enums/ — довідник choices з моделей (єдине джерело істини для фронту).
    Дозволяє не дублювати списки в src/utils/constants.js.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from clients.models import Truck
        from orders.models import TruckMaintenanceIntervals

        def _to_options(choices):
            return [{'value': v, 'label': l} for v, l in choices]

        return Response({
            'euro_standards':     _to_options(Truck.EURO_STANDARD_CHOICES),
            'transmission_types': _to_options(Truck.TRANSMISSION_CHOICES),
            'tracking_modes':     _to_options(TruckMaintenanceIntervals.TrackingMode.choices),
        })


def _get_backup_dir():
    backup_dir = getattr(settings, 'BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups'))
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def _backup_info(filepath):
    stat = os.stat(filepath)
    return {
        'filename': os.path.basename(filepath),
        'size': stat.st_size,
        'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


class BackupListCreateView(APIView):
    """
    GET  /api/backups/      — list all backups
    POST /api/backups/      — create a new backup
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        backup_dir = _get_backup_dir()
        backups = []
        for f in sorted(os.listdir(backup_dir), reverse=True):
            if f.endswith('.json') and f.startswith('backup_'):
                backups.append(_backup_info(os.path.join(backup_dir, f)))
        return Response(backups)

    def post(self, request):
        backup_dir = _get_backup_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.json'
        filepath = os.path.join(backup_dir, filename)

        buf = io.StringIO()
        call_command(
            'dumpdata',
            '--natural-foreign',
            '--natural-primary',
            '--exclude=contenttypes',
            '--exclude=auth.permission',
            '--exclude=admin.logentry',
            '--exclude=sessions.session',
            '--indent=2',
            stdout=buf,
        )
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(buf.getvalue())

        return Response(_backup_info(filepath), status=status.HTTP_201_CREATED)


class BackupDetailView(APIView):
    """
    GET    /api/backups/<filename>/download/  — download backup
    DELETE /api/backups/<filename>/           — delete backup
    """
    permission_classes = [IsAdminUser]

    def _get_filepath(self, filename):
        if not filename.startswith('backup_') or not filename.endswith('.json'):
            return None
        safe_name = os.path.basename(filename)
        filepath = os.path.join(_get_backup_dir(), safe_name)
        if not os.path.isfile(filepath):
            return None
        return filepath

    def delete(self, request, filename):
        filepath = self._get_filepath(filename)
        if not filepath:
            return Response({'detail': 'Backup not found.'}, status=status.HTTP_404_NOT_FOUND)
        os.remove(filepath)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BackupDownloadView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, filename):
        safe_name = os.path.basename(filename)
        if not safe_name.startswith('backup_') or not safe_name.endswith('.json'):
            return Response({'detail': 'Backup not found.'}, status=status.HTTP_404_NOT_FOUND)
        filepath = os.path.join(_get_backup_dir(), safe_name)
        if not os.path.isfile(filepath):
            return Response({'detail': 'Backup not found.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            open(filepath, 'rb'),
            as_attachment=True,
            filename=safe_name,
            content_type='application/json',
        )


class BackupRestoreView(APIView):
    """
    POST /api/backups/restore/
      - body: { "filename": "backup_20260706_120000.json" }
      - OR multipart upload with file field "file"
    """
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser] + APIView.parser_classes

    def post(self, request):
        uploaded = request.FILES.get('file')
        filename = request.data.get('filename')

        if uploaded:
            content = uploaded.read().decode('utf-8')
            try:
                json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return Response(
                    {'detail': 'Invalid backup file format.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif filename:
            safe_name = os.path.basename(filename)
            filepath = os.path.join(_get_backup_dir(), safe_name)
            if not os.path.isfile(filepath):
                return Response({'detail': 'Backup not found.'}, status=status.HTTP_404_NOT_FOUND)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            return Response(
                {'detail': 'Provide "filename" or upload a "file".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            call_command('flush', '--no-input')

            tmp_path = os.path.join(_get_backup_dir(), '_restore_tmp.json')
            with open(tmp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            try:
                call_command('loaddata', tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            return Response({'detail': 'Database restored successfully.'})
        except Exception as e:
            return Response(
                {'detail': f'Restore failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
