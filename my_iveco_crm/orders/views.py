import logging
import datetime

from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from users.permissions import IsAdminRole, IsManagerOrAbove
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django_filters.rest_framework import DjangoFilterBackend

logger = logging.getLogger(__name__)


def _filters_for_service_type(kit_filters_qs, service_type):
    """Повертає фільтри набору ТО залежно від виду ТО.

    full    → service_type in ('full', 'both')
    partial → service_type in ('partial', 'both')
    None    → всі фільтри (зворотна сумісність)
    """
    if service_type == 'full':
        return kit_filters_qs.filter(service_type__in=['full', 'both'])
    if service_type == 'partial':
        return kit_filters_qs.filter(service_type__in=['partial', 'both'])
    return kit_filters_qs.all()

from .models import (
    ServiceOrder, ServiceWork, WorkGroup, WorkPrice,
    RepairPhoto, MaintenanceRule, MaintenanceLog, MaintenanceKit, MaintenanceKitFilter,
    BaseMaintenanceKit, BaseMaintenanceKitFilter,
    TruckMaintenanceIntervals,
    OrderStatusHistory,
)
from clients.models import Truck
from inventory.models import UsedPart
from .serializers import (
    ServiceOrderListSerializer,
    ServiceOrderDetailSerializer,
    ServiceOrderWriteSerializer,
    ServiceWorkSerializer,
    ServiceWorkWriteSerializer,
    WorkGroupSerializer,
    WorkPriceSerializer,
    RepairPhotoSerializer,
    MaintenanceRuleSerializer,
    MaintenanceLogSerializer,
    MaintenanceKitSerializer,
    MaintenanceKitWriteSerializer,
    MaintenanceKitFilterSerializer,
    BaseMaintenanceKitSerializer,
    BaseMaintenanceKitWriteSerializer,
    BaseMaintenanceKitFilterSerializer,
    UsedPartSerializer,
    TruckMaintenanceIntervalsSerializer,
    OrderStatusHistorySerializer,
)


class ServiceOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet для роботи з нарядами-замовленнями.
    Виправлено: додано truck__client до select_related для оптимізації запитів.
    """
    queryset = ServiceOrder.objects.select_related(
        'client', 
        'truck',
        'truck__client',  # Додано для оптимізації запитів до клієнта вантажівки
        'marked_for_deletion_by'
    ).all().order_by('-created_at')
    
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsManagerOrAbove()]
        return [permissions.IsAuthenticated()]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = [
        'order_number',
        'truck__license_plate', 
        'client__name',
    ]
    filterset_fields = ['status', 'client', 'truck', 'marked_for_deletion']
    ordering_fields = ['created_at', 'order_number', 'status']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceOrderListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceOrderWriteSerializer
        return ServiceOrderDetailSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if self.action == 'retrieve':
            queryset = queryset.prefetch_related(
                'works', 'works__work', 'works__mechanic',
                'works__used_parts', 'works__used_parts__part', 'photos',
                'direct_parts', 'direct_parts__part',
            )
            return queryset
            
        if self.action == 'list':
            queryset = queryset.prefetch_related('photos')
            marked_param = self.request.query_params.get('marked_for_deletion')
            if str(marked_param).lower() != 'true':
                queryset = queryset.filter(marked_for_deletion=False)
            
        global_search = self.request.query_params.get('global_search', None)
        if global_search:
            queryset = queryset.filter(
                Q(order_number__icontains=global_search) |
                Q(truck__license_plate__icontains=global_search) |
                Q(client__name__icontains=global_search)
            )
        return queryset

    def perform_create(self, serializer):
        """При створенні фіксуємо автора початкового статусу."""
        instance = serializer.save()
        OrderStatusHistory.objects.filter(
            order=instance, from_status=''
        ).update(changed_by=self.request.user)

    def perform_update(self, serializer):
        """Передаємо поточного користувача в сигнал для запису автора зміни статусу."""
        serializer.instance._changed_by = self.request.user
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Фізичне видалення заборонено. Використовуйте позначення на видалення."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=True, methods=['get'], url_path='status-history')
    def status_history(self, request, pk=None):
        """Хронологія змін статусу замовлення."""
        order = self.get_object()
        history = order.status_history.select_related('changed_by').order_by('changed_at')
        serializer = OrderStatusHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='search-truck')
    def search_truck(self, request):
        """Пошук вантажівки за номерним знаком."""
        plate_query = request.query_params.get('plate', '').strip()
        if len(plate_query) < 2:
            return Response({'results': []}, status=status.HTTP_200_OK)

        trucks = Truck.objects.select_related('client').filter(
            license_plate__icontains=plate_query
        )[:10]

        results = []
        for truck in trucks:
            results.append({
                'id': truck.id,
                'license_plate': truck.license_plate,
                'model': truck.specific_model_name,
                'vin': truck.last_seven_vin,
                'client_id': truck.client.id if truck.client else None,
                'client_name': truck.client.name if truck.client else "Без власника"
            })
        return Response({'results': results})

    @action(detail=False, methods=['post'], url_path='check-maintenance')
    def check_maintenance(self, request):
        """Перевірка необхідності ТО."""
        return Response({'alerts': []})

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Статистика для дашборду."""
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)

        qs = ServiceOrder.objects.filter(marked_for_deletion=False)
        closed_qs = qs.filter(status__in=['DONE', 'CLOSED'])

        # Виторг за поточний місяць і рік
        monthly_revenue = closed_qs.filter(
            created_at__date__gte=start_of_month
        ).aggregate(total=Sum('total_cost'))['total'] or 0

        yearly_revenue = closed_qs.filter(
            created_at__date__gte=start_of_year
        ).aggregate(total=Sum('total_cost'))['total'] or 0

        # Графік виторгу за останні 12 місяців
        revenue_chart = []
        for i in range(11, -1, -1):
            month_date = (today.replace(day=1) - datetime.timedelta(days=i * 28)).replace(day=1)
            if month_date.month == 12:
                next_month = month_date.replace(year=month_date.year + 1, month=1)
            else:
                next_month = month_date.replace(month=month_date.month + 1)
            revenue = closed_qs.filter(
                created_at__date__gte=month_date,
                created_at__date__lt=next_month,
            ).aggregate(total=Sum('total_cost'))['total'] or 0
            ua_months = ['Січ', 'Лют', 'Бер', 'Кві', 'Тра', 'Чер',
                         'Лип', 'Сер', 'Вер', 'Жов', 'Лис', 'Гру']
            revenue_chart.append({
                'name': ua_months[month_date.month - 1],
                'revenue': float(revenue),
            })

        stats = {
            'total_orders': qs.count(),
            'open_orders': qs.filter(status='OPEN').count(),
            'in_progress_orders': qs.filter(status='IN_PROGRESS').count(),
            'closed_orders': qs.filter(status='CLOSED').count(),
            'canceled_orders': qs.filter(status='CANCELED').count(),
            'monthly_revenue': float(monthly_revenue),
            'yearly_revenue': float(yearly_revenue),
            'revenue_chart': revenue_chart,
        }
        return Response(stats)

    @action(detail=False, methods=['get'])
    def week_detail(self, request):
        """Кількість замовлень по днях поточного тижня (Пн–Нд)."""
        today = timezone.now().date()
        qs = ServiceOrder.objects.filter(marked_for_deletion=False)
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']
        sunday = monday + datetime.timedelta(days=6)
        counts = {
            r['day']: r['count']
            for r in ServiceOrder.objects
            .filter(marked_for_deletion=False, created_at__date__gte=monday, created_at__date__lte=sunday)
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(count=Count('id'))
        }
        result = [
            {'name': day_names[i], 'orders': counts.get(monday + datetime.timedelta(days=i), 0)}
            for i in range(7)
        ]
        return Response(result)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Підсумок кількості замовлень за день, тиждень, місяць та рік."""
        today = timezone.now().date()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)

        qs = ServiceOrder.objects.filter(marked_for_deletion=False)
        return Response({
            'today': qs.filter(created_at__date=today).count(),
            'week': qs.filter(created_at__date__gte=start_of_week).count(),
            'month': qs.filter(created_at__date__gte=start_of_month).count(),
            'year': qs.filter(created_at__date__gte=start_of_year).count(),
        })

    @action(detail=True, methods=['post'])
    def mark_for_deletion(self, request, pk=None):
        """Позначити замовлення на видалення."""
        order = self.get_object()
        order.marked_for_deletion = True
        order.marked_for_deletion_by = request.user
        order.marked_for_deletion_at = timezone.now()
        order.deletion_reason = request.data.get('reason', '')
        order.save()
        return Response({'status': 'success'})
    
    @action(detail=True, methods=['post'])
    def unmark_for_deletion(self, request, pk=None):
        """Зняти позначку на видалення."""
        order = self.get_object()
        order.marked_for_deletion = False
        order.deletion_reason = ''
        order.marked_for_deletion_by = None
        order.marked_for_deletion_at = None
        order.save()
        return Response({'status': 'success'})
    
    def _build_order_pdf(self, order, mode='client'):
        """
        Будує PDF наряду-замовлення.
        mode='client'   — з цінами, підсумками, рекомендаціями та підписами
        mode='mechanic' — без цін, запчастини згруповані під кожною роботою
        """
        from django.http import HttpResponse
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from inventory.models import UsedPart
        import io
        import os

        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/TTF/DejaVuSans.ttf',
            'C:/Windows/Fonts/arial.ttf',
        ]
        font_name = 'Helvetica'
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont('CustomFont', fp))
                    font_name = 'CustomFont'
                except Exception:
                    pass
                break

        Y_COLOR = colors.HexColor('#f5c518')
        INK = colors.HexColor('#1a1a1a')
        GRAY = colors.HexColor('#888888')
        LIGHT = colors.HexColor('#f7f7f7')
        GRID_COLOR = colors.HexColor('#e0e0e0')

        h2 = ParagraphStyle('h2', fontName=font_name, fontSize=11, textColor=INK, spaceAfter=2, spaceBefore=8)
        normal = ParagraphStyle('normal', fontName=font_name, fontSize=9, textColor=INK, leading=14)
        small = ParagraphStyle('small', fontName=font_name, fontSize=8, textColor=GRAY)
        indent = ParagraphStyle('indent', fontName=font_name, fontSize=8, textColor=GRAY, leftIndent=4)

        status_labels = {
            'OPEN': 'Відкрито', 'IN_PROGRESS': 'В роботі',
            'DONE': 'Виконано', 'CLOSED': 'Закрито', 'CANCELED': 'Скасовано',
        }

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf, pagesize=A4,
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=15*mm, bottomMargin=15*mm,
        )

        story = []

        # ── Шапка ────────────────────────────────────────────────────────
        subtitle = 'Завдання механіку' if mode == 'mechanic' else 'Наряд-замовлення'
        header_data = [[
            Paragraph('<b>Іта́л Трак</b> — Сервісний центр Iveco',
                      ParagraphStyle('brand', fontName=font_name, fontSize=13, textColor=INK)),
            Paragraph(f'<b>{subtitle}</b><br/>№ {order.order_number or order.id}',
                      ParagraphStyle('num', fontName=font_name, fontSize=12, textColor=INK, alignment=2)),
        ]]
        ht = Table(header_data, colWidths=[100*mm, 80*mm])
        ht.setStyle(TableStyle([
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 2, Y_COLOR),
        ]))
        story.append(ht)
        story.append(Spacer(1, 6*mm))

        # ── Інформація про замовлення ─────────────────────────────────────
        story.append(Paragraph('Інформація про замовлення', h2))
        info_rows = [
            ['Статус', status_labels.get(order.status, order.status)],
            ['Дата створення', order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '—'],
            ['Клієнт', order.client.name if order.client else '—'],
            ['Телефон', order.client.phone or '—' if order.client else '—'],
            ['Вантажівка', str(order.truck) if order.truck else '—'],
            ['Номерний знак', order.truck.license_plate if order.truck else '—'],
            ['Пробіг', f'{order.current_mileage:,} км'.replace(',', ' ') if order.current_mileage else '—'],
        ]
        it = Table(
            [[Paragraph(f'<b>{r[0]}</b>', normal), Paragraph(str(r[1]), normal)] for r in info_rows],
            colWidths=[50*mm, 130*mm],
        )
        it.setStyle(TableStyle([
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.5, GRID_COLOR),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(it)

        # ── Опис проблеми ─────────────────────────────────────────────────
        if order.problem_description:
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph('Опис проблеми', h2))
            story.append(Paragraph(order.problem_description, normal))

        # ── Вибірка даних ─────────────────────────────────────────────────
        works = list(order.works.select_related('work__work_group').prefetch_related('used_parts__part').all())
        direct_parts = list(
            UsedPart.objects.filter(service_order=order, service_work__isnull=True)
            .select_related('part')
        )

        # ══════════════════════════════════════════════════════════════════
        if mode == 'mechanic':
            # ── Роботи та матеріали (для механіка) ───────────────────────
            if works or direct_parts:
                story.append(Spacer(1, 4*mm))
                story.append(Paragraph('Роботи та матеріали', h2))

            for idx, w in enumerate(works, 1):
                work_name = w.work.name if w.work else (w.description or '—')
                # Рядок роботи
                wrow = Table(
                    [[Paragraph(f'<b>{idx}. {work_name}</b>', normal),
                      Paragraph(f'{w.hours_spent} год.', normal)]],
                    colWidths=[150*mm, 30*mm],
                )
                wrow.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), Y_COLOR),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                    ('RIGHTPADDING', (1, 0), (1, 0), 8),
                ]))
                story.append(wrow)

                # Запчастини для цієї роботи
                parts = list(w.used_parts.all())
                if parts:
                    parts_data = [[
                        Paragraph('<b>Артикул</b>', indent),
                        Paragraph('<b>Найменування</b>', indent),
                        Paragraph('<b>К-сть</b>', indent),
                    ]]
                    for p in parts:
                        parts_data.append([
                            Paragraph(p.part.sku_code or '—', indent),
                            Paragraph(p.part.name, indent),
                            Paragraph(str(p.quantity), indent),
                        ])
                    pt = Table(parts_data, colWidths=[35*mm, 120*mm, 25*mm])
                    pt.setStyle(TableStyle([
                        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [LIGHT, colors.white]),
                        ('GRID', (0, 0), (-1, -1), 0.3, GRID_COLOR),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                        ('RIGHTPADDING', (2, 0), (2, -1), 8),
                    ]))
                    story.append(pt)
                else:
                    story.append(Table(
                        [[Paragraph('— запчастини не вказані —', indent)]],
                        colWidths=[180*mm],
                    ))
                story.append(Spacer(1, 2*mm))

            # Запчастини без прив'язки до роботи
            if direct_parts:
                story.append(Spacer(1, 2*mm))
                story.append(Paragraph('Додаткові матеріали', h2))
                dp_data = [[
                    Paragraph('<b>Артикул</b>', normal),
                    Paragraph('<b>Найменування</b>', normal),
                    Paragraph('<b>К-сть</b>', normal),
                ]]
                for p in direct_parts:
                    dp_data.append([
                        Paragraph(p.part.sku_code or '—', normal),
                        Paragraph(p.part.name, normal),
                        Paragraph(str(p.quantity), normal),
                    ])
                dpt = Table(dp_data, colWidths=[35*mm, 120*mm, 25*mm])
                dpt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), Y_COLOR),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
                    ('GRID', (0, 0), (-1, -1), 0.5, GRID_COLOR),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
                ]))
                story.append(dpt)

        # ══════════════════════════════════════════════════════════════════
        else:  # mode == 'client'
            # ── Виконані роботи (для клієнта) ────────────────────────────
            if works:
                story.append(Spacer(1, 4*mm))
                story.append(Paragraph('Виконані роботи', h2))
                work_data = [[
                    Paragraph('<b>Найменування роботи</b>', normal),
                    Paragraph('<b>Год.</b>', normal),
                    Paragraph('<b>Ціна/год.</b>', normal),
                    Paragraph('<b>Сума</b>', normal),
                ]]
                works_total = sum(w.amount for w in works)
                for w in works:
                    name = w.work.name if w.work else (w.description or '—')
                    work_data.append([
                        Paragraph(name, normal),
                        Paragraph(str(w.hours_spent), normal),
                        Paragraph(f'{float(w.price_at_moment):,.0f} ₴', normal),
                        Paragraph(f'{float(w.amount):,.0f} ₴', normal),
                    ])
                work_data.append([
                    Paragraph('<b>Разом за роботи</b>', normal), '', '',
                    Paragraph(f'<b>{float(works_total):,.0f} ₴</b>', normal),
                ])
                wt = Table(work_data, colWidths=[95*mm, 20*mm, 30*mm, 35*mm])
                wt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), Y_COLOR),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, LIGHT]),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffbea')),
                    ('GRID', (0, 0), (-1, -1), 0.5, GRID_COLOR),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('SPAN', (0, -1), (2, -1)),
                    ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ]))
                story.append(wt)

            # ── Використані запчастини (для клієнта) ─────────────────────
            all_parts = [p for w in works for p in w.used_parts.all()] + direct_parts
            if all_parts:
                story.append(Spacer(1, 4*mm))
                story.append(Paragraph('Використані запчастини', h2))
                parts_data = [[
                    Paragraph('<b>Артикул</b>', normal),
                    Paragraph('<b>Найменування</b>', normal),
                    Paragraph('<b>К-сть</b>', normal),
                    Paragraph('<b>Ціна</b>', normal),
                    Paragraph('<b>Сума</b>', normal),
                ]]
                parts_total = 0
                for p in all_parts:
                    unit_price = float(p.unit_price or p.part.selling_price or 0)
                    total = float(p.quantity) * unit_price
                    parts_total += total
                    parts_data.append([
                        Paragraph(p.part.sku_code or '—', normal),
                        Paragraph(p.part.name, normal),
                        Paragraph(str(p.quantity), normal),
                        Paragraph(f'{unit_price:,.0f} ₴', normal),
                        Paragraph(f'{total:,.0f} ₴', normal),
                    ])
                parts_data.append([
                    Paragraph('<b>Разом за запчастини</b>', normal), '', '', '',
                    Paragraph(f'<b>{parts_total:,.0f} ₴</b>', normal),
                ])
                pt = Table(parts_data, colWidths=[30*mm, 75*mm, 15*mm, 25*mm, 35*mm])
                pt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), Y_COLOR),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, LIGHT]),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fffbea')),
                    ('GRID', (0, 0), (-1, -1), 0.5, GRID_COLOR),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('SPAN', (0, -1), (3, -1)),
                    ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ]))
                story.append(pt)

            # ── Загальна сума ─────────────────────────────────────────────
            if works or all_parts:
                story.append(Spacer(1, 3*mm))
                tt = Table([[
                    Paragraph('<b>ЗАГАЛЬНА СУМА</b>',
                              ParagraphStyle('tl', fontName=font_name, fontSize=11, textColor=INK)),
                    Paragraph(f'<b>{float(order.total_cost):,.0f} ₴</b>',
                              ParagraphStyle('tv', fontName=font_name, fontSize=11, textColor=INK, alignment=2)),
                ]], colWidths=[140*mm, 40*mm])
                tt.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), Y_COLOR),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(tt)

            # ── Рекомендації ──────────────────────────────────────────────
            if order.recommendations:
                story.append(Spacer(1, 4*mm))
                story.append(Paragraph('Рекомендації', h2))
                story.append(Paragraph(order.recommendations, normal))

        # ── Підпис (обидва режими) ────────────────────────────────────────
        story.append(Spacer(1, 10*mm))
        story.append(HRFlowable(width='100%', thickness=1, color=GRID_COLOR))
        story.append(Spacer(1, 4*mm))
        left_label = 'Підпис клієнта: ____________________' if mode == 'client' else 'Перевірив майстер: ____________________'
        st = Table(
            [[Paragraph(left_label, small),
              Paragraph('Виконавець (механік): ____________________', small)]],
            colWidths=[90*mm, 90*mm],
        )
        story.append(st)

        doc.build(story)
        buf.seek(0)
        suffix = 'mechanic' if mode == 'mechanic' else 'client'
        filename = f'order_{order.order_number or order.id}_{suffix}.pdf'
        response = HttpResponse(buf.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'], url_path='pdf')
    def export_pdf(self, request, pk=None):
        """PDF для клієнта — з цінами, підсумками та рекомендаціями."""
        return self._build_order_pdf(self.get_object(), mode='client')

    @action(detail=True, methods=['get'], url_path='pdf-mechanic')
    def export_pdf_mechanic(self, request, pk=None):
        """PDF для механіка — без цін, запчастини під кожною роботою."""
        return self._build_order_pdf(self.get_object(), mode='mechanic')

    @action(detail=True, methods=['post'])
    def add_work(self, request, pk=None):
        """Додати роботу до замовлення."""
        order = self.get_object()
        serializer = ServiceWorkWriteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(service_order=order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='apply_maintenance_set')
    def apply_maintenance_set(self, request, pk=None):
        """Застосувати набір ТО до наряду.

        Параметри:
            rule_id (int): обовʼязковий
            service_type (str): 'full' | 'partial' — вид ТО (за замовч. всі фільтри)
        """
        order = self.get_object()
        rule_id = request.data.get('rule_id')
        service_type = request.data.get('service_type')  # 'full' | 'partial' | None

        if not rule_id:
            return Response({'detail': 'rule_id є обовʼязковим'}, status=status.HTTP_400_BAD_REQUEST)

        if service_type and service_type not in ('full', 'partial'):
            return Response({'detail': "service_type має бути 'full' або 'partial'"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rule = MaintenanceRule.objects.get(id=rule_id)
        except MaintenanceRule.DoesNotExist:
            return Response({'detail': 'Правило ТО не знайдено'}, status=status.HTTP_404_NOT_FOUND)

        try:
            kit = MaintenanceKit.objects.prefetch_related('filters').get(truck=order.truck)
        except MaintenanceKit.DoesNotExist:
            return Response(
                {'detail': 'Для цього авто не налаштовано комплект ТО. Додайте комплект у картці авто.'},
                status=status.HTTP_404_NOT_FOUND
            )

        applicable_filters = _filters_for_service_type(kit.filters, service_type)

        # Очищаємо старі direct_parts цього наряду від запчастин набору ТО
        from inventory.services import StockService
        kit_part_ids = [kit.oil_id] + list(applicable_filters.values_list('part_id', flat=True))
        for old_part in UsedPart.objects.filter(
            service_order=order,
            service_work__isnull=True,
            part_id__in=kit_part_ids,
        ):
            StockService.restore(old_part)
            old_part.delete()

        # Видаляємо попередньо застосований набір (якщо є), щоб уникнути дублювання
        ServiceWork.objects.filter(service_order=order, description=rule.name).delete()

        # Створюємо роботу для ТО
        service_work = ServiceWork.objects.create(
            service_order=order,
            description=rule.name,
            hours_spent=0,
            price_at_moment=0,
        )

        # Додаємо оливу та фільтри до роботи
        oil_part = UsedPart.objects.create(
            service_work=service_work,
            part=kit.oil,
            quantity=kit.oil_quantity,
        )
        StockService.deduct(oil_part)

        for kit_filter in applicable_filters:
            filter_part = UsedPart.objects.create(
                service_work=service_work,
                part=kit_filter.part,
                quantity=kit_filter.quantity,
            )
            StockService.deduct(filter_part)

        # Логуємо виконання ТО
        MaintenanceLog.objects.create(
            truck=order.truck,
            rule=rule,
            date_performed=timezone.now().date(),
            mileage=order.current_mileage,
        )

        order.update_total_cost()

        type_label = {'full': 'повне', 'partial': 'часткове'}.get(service_type, '')
        label = f' ({type_label})' if type_label else ''
        return Response(
            {'detail': f'Набір ТО "{rule.name}"{label} застосовано до наряду'},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get'], url_path='maintenance-countdown')
    def maintenance_countdown(self, request, pk=None):
        """Повертає відлік регламентних робіт для замовлення."""
        order = self.get_object()
        current_km = order.current_mileage

        try:
            intervals = order.truck.maintenance_intervals
        except TruckMaintenanceIntervals.DoesNotExist:
            intervals = None

        TYPES = [
            ('engine_oil',    'До заміни оливи в двигуні'),
            ('rear_axle_oil', 'До заміни оливи в задньому мості'),
            ('belts',         'До заміни ремнів/роликів'),
            ('chains',        'До заміни ланцюгів'),
        ]

        result = []

        # Визначаємо тип КПП за заповненістю полів інтервалів
        has_auto = intervals and intervals.auto_gearbox_oil_interval is not None
        has_manual = intervals and intervals.gearbox_oil_interval is not None
        if has_auto and not has_manual:
            gearbox_types = [('auto_gearbox_oil', 'До заміни оливи в АКПП')]
        elif has_manual and not has_auto:
            gearbox_types = [('gearbox_oil', 'До заміни оливи в КПП')]
        elif has_auto and has_manual:
            gearbox_types = [
                ('gearbox_oil',      'До заміни оливи в КПП'),
                ('auto_gearbox_oil', 'До заміни оливи в АКПП'),
            ]
        else:
            gearbox_types = [('gearbox_oil', 'До заміни оливи в КПП/АКПП')]

        all_types = [TYPES[0]] + gearbox_types + TYPES[1:]

        for key, label in all_types:
            interval = getattr(intervals, f'{key}_interval', None) if intervals else None
            last_km  = getattr(intervals, f'{key}_last_km', None) if intervals else None

            if interval is not None and last_km is not None and current_km is not None:
                remaining = last_km + interval - current_km
            else:
                remaining = None

            result.append({
                'key': key,
                'label': label,
                'interval': interval,
                'last_km': last_km,
                'remaining': remaining,
            })

        return Response({
            'current_km': current_km,
            'items': result,
        })


class ServiceWorkViewSet(viewsets.ModelViewSet):
    """ViewSet для роботи з виконаними роботами."""
    queryset = ServiceWork.objects.select_related(
        'service_order', 'work', 'mechanic'
    ).all()
    serializer_class = ServiceWorkSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ServiceWorkWriteSerializer
        return ServiceWorkSerializer

    @action(detail=True, methods=['post'], url_path='add-part')
    def add_part(self, request, pk=None):
        """Додати запчастину до роботи."""
        service_work = self.get_object()
        part_id = request.data.get('part')
        quantity = request.data.get('quantity', 1)
        unit_price = request.data.get('unit_price')
        
        try:
            from inventory.services import StockService
            used_part = UsedPart.objects.create(
                service_work=service_work,
                part_id=part_id,
                quantity=quantity,
                unit_price=unit_price
            )
            StockService.deduct(used_part)
            return Response(UsedPartSerializer(used_part).data, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['delete'], url_path='remove-part/(?P<part_id>[^/.]+)')
    def remove_part(self, request, pk=None, part_id=None):
        """Видалити запчастину з роботи."""
        try:
            from inventory.services import StockService
            used_part = UsedPart.objects.get(id=part_id, service_work_id=pk)
            StockService.restore(used_part)
            used_part.delete()
            return Response(status=204)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

    @action(detail=True, methods=['post'], url_path='apply-kit')
    def apply_kit(self, request, pk=None):
        """Вручну додати набір ТО (оливу + фільтри) до роботи.

        Параметри:
            service_type (str): 'full' | 'partial' — вид ТО (за замовч. всі фільтри)
        """
        work = self.get_object()
        truck = work.service_order.truck
        service_type = request.data.get('service_type')  # 'full' | 'partial' | None

        if not truck:
            return Response({'error': 'Вантажівка не вказана в замовленні'}, status=status.HTTP_400_BAD_REQUEST)

        if service_type and service_type not in ('full', 'partial'):
            return Response({'error': "service_type має бути 'full' або 'partial'"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            kit = MaintenanceKit.objects.prefetch_related('filters__part').get(truck=truck)
        except MaintenanceKit.DoesNotExist:
            return Response(
                {'error': f'Набір ТО для {truck.license_plate} не знайдено. Спочатку збережіть набір.'},
                status=status.HTTP_404_NOT_FOUND
            )

        from inventory.services import StockService
        added = []

        if kit.oil:
            oil_part, created = UsedPart.objects.get_or_create(
                service_work=work,
                part=kit.oil,
                defaults={'quantity': kit.oil_quantity}
            )
            if created:
                StockService.deduct(oil_part)
            added.append({'name': kit.oil.name, 'quantity': str(kit.oil_quantity), 'type': 'oil'})

        applicable_filters = _filters_for_service_type(kit.filters, service_type)
        for kit_filter in applicable_filters:
            filter_part, created = UsedPart.objects.get_or_create(
                service_work=work,
                part=kit_filter.part,
                defaults={'quantity': kit_filter.quantity}
            )
            if created:
                StockService.deduct(filter_part)
            added.append({'name': kit_filter.part.name, 'quantity': kit_filter.quantity, 'type': 'filter'})

        work.service_order.update_total_cost()

        return Response({'added': added, 'count': len(added)}, status=status.HTTP_200_OK)


class WorkGroupViewSet(viewsets.ModelViewSet):
    """ViewSet для груп робіт."""
    queryset = WorkGroup.objects.all()
    serializer_class = WorkGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsAdminRole()]
        return [permissions.IsAuthenticated()]


class WorkPriceViewSet(viewsets.ModelViewSet):
    """ViewSet для цін на роботи."""
    queryset = WorkPrice.objects.select_related('work_group').all()
    serializer_class = WorkPriceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated(), IsAdminRole()]
        return [permissions.IsAuthenticated()]


class RepairPhotoViewSet(viewsets.ModelViewSet):
    """ViewSet для фото ремонту."""
    queryset = RepairPhoto.objects.select_related('service_order').all()
    serializer_class = RepairPhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='bulk_upload')
    def bulk_upload(self, request):
        """Завантаження кількох фото одночасно. Надсилає одне сповіщення клієнту."""
        import traceback
        import warnings
        from .models import ServiceOrder
        try:
            from .models import MAX_REPAIR_PHOTOS_PER_ORDER
        except ImportError:
            MAX_REPAIR_PHOTOS_PER_ORDER = 20

        images = request.FILES.getlist('images')
        service_order_id = request.data.get('service_order')
        description = request.data.get('description', '')

        if not images:
            return Response({'error': 'No images provided'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = ServiceOrder.objects.get(pk=service_order_id)
        except (ServiceOrder.DoesNotExist, Exception) as e:
            if not isinstance(e, ServiceOrder.DoesNotExist):
                import traceback, warnings
                warnings.warn(f"bulk_upload order query error: {traceback.format_exc()}")
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        current_count = order.photos.count()
        remaining = MAX_REPAIR_PHOTOS_PER_ORDER - current_count
        if remaining <= 0:
            return Response(
                {'error': f'Максимальна кількість фото на наряд — {MAX_REPAIR_PHOTOS_PER_ORDER}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        images = images[:remaining]
        created_photos = []
        try:
            for image in images:
                photo = RepairPhoto(service_order=order, image=image, description=description)
                photo._skip_notification = True
                photo.save()
                created_photos.append(photo)

            # Надсилаємо одне сповіщення після завантаження всіх фото
            if created_photos:
                from .signals import notify_client_on_new_photo
                representative = created_photos[0]
                representative._skip_notification = False
                notify_client_on_new_photo(sender=RepairPhoto, instance=representative, created=True)
        except Exception as e:
            tb = traceback.format_exc()
            warnings.warn(f"bulk_upload error: {e}\n{tb}")
            return Response({'error': str(e), 'detail': tb}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = RepairPhotoSerializer(created_photos, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MaintenanceRuleViewSet(viewsets.ModelViewSet):
    """ViewSet для правил ТО."""
    queryset = MaintenanceRule.objects.all()
    serializer_class = MaintenanceRuleSerializer
    permission_classes = [permissions.IsAuthenticated]


class MaintenanceLogViewSet(viewsets.ModelViewSet):
    """ViewSet для журналу ТО."""
    queryset = MaintenanceLog.objects.select_related('truck', 'rule').order_by('-date_performed')
    serializer_class = MaintenanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['truck']


class MaintenanceKitViewSet(viewsets.ModelViewSet):
    """ViewSet для комплектів ТО."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['truck']

    def get_queryset(self):
        return MaintenanceKit.objects.select_related(
            'truck', 'oil'
        ).prefetch_related(
            'filters', 'filters__part'
        ).all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MaintenanceKitWriteSerializer
        return MaintenanceKitSerializer

    @action(detail=True, methods=['post'], url_path='add-filter')
    def add_filter(self, request, pk=None):
        """Додати фільтр до комплекту ТО."""
        kit = self.get_object()
        serializer = MaintenanceKitFilterSerializer(data={**request.data, 'maintenance_kit': kit.pk})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove-filter/(?P<filter_id>[^/.]+)')
    def remove_filter(self, request, pk=None, filter_id=None):
        """Видалити фільтр з комплекту ТО."""
        try:
            MaintenanceKitFilter.objects.get(id=filter_id, maintenance_kit_id=pk).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except MaintenanceKitFilter.DoesNotExist:
            return Response({'error': 'Фільтр не знайдено'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='suggest')
    def suggest(self, request):
        """Повертає базовий шаблон комплекту ТО для конкретної вантажівки.

        Пошук іде за base_model + euro_standard.
        Якщо точного збігу немає — повертає шаблон без прив'язки до Євро-стандарту.
        """
        truck_id = request.query_params.get('truck_id')
        if not truck_id:
            return Response({'detail': 'truck_id є обовʼязковим'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            truck = Truck.objects.select_related('base_model').get(id=truck_id)
        except Truck.DoesNotExist:
            return Response({'detail': 'Вантажівку не знайдено'}, status=status.HTTP_404_NOT_FOUND)

        if not truck.base_model:
            return Response(
                {'detail': 'Для цієї вантажівки не вказано базову модель'},
                status=status.HTTP_404_NOT_FOUND
            )

        qs = BaseMaintenanceKit.objects.filter(
            base_model=truck.base_model
        ).select_related('oil').prefetch_related('filters', 'filters__part')

        # Спочатку — точний збіг по Євро-стандарту
        base_kit = qs.filter(euro_standard=truck.euro_standard or '').first()

        # Запасний варіант — шаблон "для будь-якого Євро" цієї моделі
        if not base_kit and truck.euro_standard:
            base_kit = qs.filter(euro_standard='').first()

        if not base_kit:
            return Response(
                {'detail': 'Базовий шаблон для цієї моделі не знайдено'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(BaseMaintenanceKitSerializer(base_kit).data)

    @action(detail=False, methods=['post'], url_path='from-base')
    def from_base(self, request):
        """Копіює базовий шаблон комплекту ТО на конкретну вантажівку.

        Приймає: { truck_id, base_kit_id }
        Якщо комплект для авто вже існує — перезаписує його.
        """
        truck_id = request.data.get('truck_id')
        base_kit_id = request.data.get('base_kit_id')

        if not truck_id or not base_kit_id:
            return Response(
                {'detail': 'truck_id та base_kit_id є обовʼязковими'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            truck = Truck.objects.get(id=truck_id)
        except Truck.DoesNotExist:
            return Response({'detail': 'Вантажівку не знайдено'}, status=status.HTTP_404_NOT_FOUND)

        try:
            base_kit = BaseMaintenanceKit.objects.prefetch_related('filters').get(id=base_kit_id)
        except BaseMaintenanceKit.DoesNotExist:
            return Response({'detail': 'Базовий шаблон не знайдено'}, status=status.HTTP_404_NOT_FOUND)

        kit, created = MaintenanceKit.objects.update_or_create(
            truck=truck,
            defaults={
                'oil': base_kit.oil,
                'oil_quantity': base_kit.oil_quantity,
                'oil_change_interval_km': base_kit.oil_change_interval_km,
            }
        )

        # Замінюємо фільтри копією з шаблону (зберігаємо service_type)
        kit.filters.all().delete()
        for f in base_kit.filters.all():
            MaintenanceKitFilter.objects.create(
                maintenance_kit=kit,
                part=f.part,
                quantity=f.quantity,
                change_interval_km=f.change_interval_km,
                service_type=f.service_type,
            )

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(MaintenanceKitSerializer(
            MaintenanceKit.objects.prefetch_related('filters', 'filters__part').get(pk=kit.pk)
        ).data, status=response_status)


class MaintenanceKitFilterViewSet(viewsets.ModelViewSet):
    """ViewSet для окремих фільтрів комплекту ТО."""
    serializer_class = MaintenanceKitFilterSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['maintenance_kit']

    def get_queryset(self):
        return MaintenanceKitFilter.objects.select_related(
            'maintenance_kit', 'part'
        ).all()


class TruckMaintenanceIntervalsViewSet(viewsets.ModelViewSet):
    """ViewSet для інтервалів ТО."""
    serializer_class = TruckMaintenanceIntervalsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['truck']

    def get_queryset(self):
        return TruckMaintenanceIntervals.objects.select_related('truck').all()

    @action(detail=False, methods=['put'], url_path='by-truck/(?P<truck_id>[^/.]+)')
    def by_truck(self, request, truck_id=None):
        """PUT /api/maintenance-intervals/by-truck/{truck_id}/ — update_or_create одним запитом."""
        obj, _ = TruckMaintenanceIntervals.objects.get_or_create(truck_id=truck_id)
        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class BaseMaintenanceKitViewSet(viewsets.ModelViewSet):
    """ViewSet для базових шаблонів комплектів ТО (по моделі + Євро-стандарт)."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['base_model', 'euro_standard']

    def get_queryset(self):
        return BaseMaintenanceKit.objects.select_related(
            'base_model', 'oil'
        ).prefetch_related('filters', 'filters__part').all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return BaseMaintenanceKitWriteSerializer
        return BaseMaintenanceKitSerializer

    @action(detail=True, methods=['post'], url_path='add-filter')
    def add_filter(self, request, pk=None):
        """Додати фільтр до базового шаблону."""
        base_kit = self.get_object()
        serializer = BaseMaintenanceKitFilterSerializer(
            data={**request.data, 'base_kit': base_kit.pk}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove-filter/(?P<filter_id>[^/.]+)')
    def remove_filter(self, request, pk=None, filter_id=None):
        """Видалити фільтр з базового шаблону."""
        try:
            BaseMaintenanceKitFilter.objects.get(id=filter_id, base_kit_id=pk).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except BaseMaintenanceKitFilter.DoesNotExist:
            return Response({'error': 'Фільтр не знайдено'}, status=status.HTTP_404_NOT_FOUND)
