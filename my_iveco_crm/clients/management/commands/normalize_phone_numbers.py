"""
Django management command для нормалізації телефонних номерів клієнтів в базі даних.

Перетворює всі номери до формату +380XXXXXXXXX

Приклади:
    067... -> +38067...
    0671234567 -> +380671234567
    380671234567 -> +380671234567
    (067) 123-45-67 -> +380671234567

Використання:
    python manage.py normalize_phone_numbers [--dry-run] [--verbose]

Опції:
    --dry-run    Показати що буде змінено без збереження
    --verbose    Детальний вивід кожної зміни
"""

import re
from django.core.management.base import BaseCommand
from django.db.models import Q
from clients.models import Client


class Command(BaseCommand):
    help = 'Нормалізує телефонні номери клієнтів до формату +380XXXXXXXXX'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовий запуск без збереження змін'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Детальний вивід всіх змін'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(self.style.WARNING('=' * 80))
            self.stdout.write(self.style.WARNING('ТЕСТОВИЙ РЕЖИМ (--dry-run)'))
            self.stdout.write(self.style.WARNING('Зміни НЕ будуть збережені'))
            self.stdout.write(self.style.WARNING('=' * 80 + '\n'))

        # Знаходимо всіх клієнтів з номерами телефонів
        clients_with_phones = Client.objects.exclude(
            Q(phone_number='') | Q(phone_number__isnull=True)
        )

        total_clients = clients_with_phones.count()
        self.stdout.write(f'Знайдено клієнтів з телефонами: {total_clients}\n')

        if total_clients == 0:
            self.stdout.write(self.style.SUCCESS('Немає клієнтів для обробки'))
            return

        # Статистика
        stats = {
            'total': total_clients,
            'normalized': 0,
            'already_correct': 0,
            'invalid': 0,
            'empty_after': 0
        }

        # Обробка кожного клієнта
        for client in clients_with_phones:
            original_phone = client.phone_number
            normalized_phone = self.normalize_phone_number(original_phone)

            # Якщо номер вже в правильному форматі
            if original_phone == normalized_phone and normalized_phone.startswith('+380'):
                stats['already_correct'] += 1
                if verbose:
                    self.stdout.write(f'✅ ID:{client.id} {client.name}: {original_phone} (вже правильний)')
                continue

            # Якщо нормалізація дала порожній результат
            if not normalized_phone:
                stats['invalid'] += 1
                self.stdout.write(self.style.ERROR(
                    f'❌ ID:{client.id} {client.name}: "{original_phone}" (невірний формат)'
                ))
                continue

            # Якщо номер порожній після нормалізації
            if normalized_phone == '':
                stats['empty_after'] += 1
                continue

            # Нормалізуємо
            stats['normalized'] += 1

            if verbose or not dry_run:
                self.stdout.write(self.style.SUCCESS(
                    f'🔄 ID:{client.id} {client.name}: {original_phone} -> {normalized_phone}'
                ))

            # Зберігаємо якщо не dry-run
            if not dry_run:
                client.phone_number = normalized_phone
                client.save()

        # Підсумкова статистика
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write('📊 ПІДСУМКОВА СТАТИСТИКА')
        self.stdout.write('=' * 80)
        self.stdout.write(f"Всього клієнтів з телефонами: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"✅ Вже правильні: {stats['already_correct']}"))
        self.stdout.write(self.style.SUCCESS(f"🔄 Нормалізовано: {stats['normalized']}"))

        if stats['invalid'] > 0:
            self.stdout.write(self.style.ERROR(f"❌ Невірний формат: {stats['invalid']}"))

        if stats['empty_after'] > 0:
            self.stdout.write(self.style.WARNING(f"⚠️  Порожні після нормалізації: {stats['empty_after']}"))

        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  ТЕСТОВИЙ РЕЖИМ - Зміни НЕ збережено'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Нормалізація завершена'))

        self.stdout.write('=' * 80 + '\n')

    def normalize_phone_number(self, phone):
        """
        Нормалізація номера телефону до формату +380XXXXXXXXX
        
        Приклади:
            067... -> +38067...
            0671234567 -> +380671234567
            380671234567 -> +380671234567
            +380671234567 -> +380671234567
            (067) 123-45-67 -> +380671234567
            8067... -> +38067...
        """
        if not phone:
            return ''
        
        # Прибираємо всі нецифрові символи окрім +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Якщо номер починається з +380
        if cleaned.startswith('+380'):
            if len(cleaned) == 13:  # +380XXXXXXXXX
                return cleaned
            else:
                return ''  # Невірна довжина
        
        # Якщо номер починається з 380
        if cleaned.startswith('380'):
            if len(cleaned) == 12:  # 380XXXXXXXXX
                return '+' + cleaned
            else:
                return ''
        
        # Якщо номер починається з 0
        if cleaned.startswith('0'):
            if len(cleaned) == 10:  # 0XXXXXXXXX
                return '+38' + cleaned
            else:
                return ''
        
        # Якщо номер починається з 8 (старий формат)
        if cleaned.startswith('8') and len(cleaned) == 10:
            return '+38' + cleaned[1:]  # Замінюємо 8 на +38
        
        # Якщо номер без коду (9 цифр)
        if len(cleaned) == 9 and not cleaned.startswith('0'):
            return '+380' + cleaned
        
        # Інші випадки - невірний формат
        return ''