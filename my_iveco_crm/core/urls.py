# core/urls.py

from django.urls import path

from .views import (
    ModuleListView, EnumsView,
    BackupListCreateView, BackupDetailView, BackupDownloadView, BackupRestoreView,
)

urlpatterns = [
    path('modules/', ModuleListView.as_view(), name='modules-list'),
    path('enums/', EnumsView.as_view(), name='enums'),
    path('backups/', BackupListCreateView.as_view(), name='backup-list-create'),
    path('backups/restore/', BackupRestoreView.as_view(), name='backup-restore'),
    path('backups/<str:filename>/', BackupDetailView.as_view(), name='backup-detail'),
    path('backups/<str:filename>/download/', BackupDownloadView.as_view(), name='backup-download'),
]
