# clients/management/commands/import_csv.py (Фінальна версія з перевіреним синтаксисом)

import csv
import re
from django.core.management.base import BaseCommand
from clients.models import Client, Truck, IvecoBaseModel
from django.db import transaction

class Command(BaseCommand):
    help = 'Imports clients and trucks from a specified CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the CSV file to import.')

    def handle(self, *args, **options):
        file_path = options['file_path']

        self.stdout.write(self.style.SUCCESS(f'Starting import from "{file_path}"...'))

        try:
            default_base_model = IvecoBaseModel.objects.get(name="Не визначено")
        except IvecoBaseModel.DoesNotExist:
            self.stdout.write(self.style.ERROR('ERROR: Default base model "Не визначено" not found.'))
            self.stdout.write(self.style.WARNING('Please create it in the admin panel before running the import.'))
            return

        created_clients_count, updated_clients_count, created_trucks_count, updated_trucks_count, skipped_rows = 0, 0, 0, 0, 0

        try:
            with open(file_path, mode='r', encoding='windows-1251') as csv_file:
                reader = csv.DictReader(csv_file, delimiter=';')

                for row_num, row in enumerate(reader, start=2):
                    try:
                        with transaction.atomic():
                            phone_raw = (row.get('№ Телефону 1') or '').strip()
                            phone1 = None
                            if phone_raw:
                                temp_phone = phone_raw
                                try:
                                    if 'E+' in temp_phone.upper():
                                        temp_phone = str(int(float(temp_phone.replace(',', '.'))))
                                except (ValueError, TypeError):
                                    pass

                                cleaned_phone = ''.join(filter(str.isdigit, temp_phone))

                                if cleaned_phone.startswith('80') and len(cleaned_phone) == 11:
                                    phone1 = f'+3{cleaned_phone}'
                                elif cleaned_phone.startswith('0') and len(cleaned_phone) == 10:
                                    phone1 = f'+38{cleaned_phone}'
                                elif cleaned_phone.startswith('380') and len(cleaned_phone) == 12:
                                    phone1 = f'+{cleaned_phone}'
                                elif len(cleaned_phone) >= 9:
                                    phone1 = cleaned_phone

                            full_vin = (row.get('') or '').strip()
                            if not full_vin:
                                skipped_rows += 1
                                continue

                            client_name = (row.get('Клієнт') or '').strip()
                            client_obj = None
                            if phone1:
                                client_obj, created = Client.objects.get_or_create(phone=phone1, defaults={'name': client_name})
                                if created: created_clients_count += 1
                            elif client_name:
                                existing_clients = Client.objects.filter(name=client_name, phone__isnull=True)
                                if existing_clients.exists():
                                    client_obj = existing_clients.first()
                                else:
                                    client_obj = Client.objects.create(name=client_name, phone=None)
                                    created_clients_count += 1

                            if not client_obj:
                                skipped_rows += 1
                                continue

                            specific_model = (row.get('Модель') or '').strip()
                            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', specific_model)
                            year = int(year_match.group(1)) if year_match else 2000

                            license_plate = (row.get('Держ номер') or '').strip()
                            truck_obj, created = Truck.objects.get_or_create(full_vin=full_vin, defaults={ 'client': client_obj, 'base_model': default_base_model, 'specific_model_name': specific_model, 'license_plate': license_plate, 'year_of_manufacture': year, 'transmission_type': 'manual', 'emission_standard': 'unknown' })
                            if created:
                                created_trucks_count += 1
                            else:
                                truck_obj.client = client_obj
                                truck_obj.license_plate = license_plate
                                truck_obj.save()
                                updated_trucks_count += 1

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error processing row {row_num}: {e}'))
                        skipped_rows += 1

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'ERROR: File not found at "{file_path}"'))
            return

        self.stdout.write(self.style.SUCCESS('--- Import Report ---'))
        self.stdout.write(f'Clients created: {created_clients_count}')
        self.stdout.write(f'Trucks created: {created_trucks_count}')
        self.stdout.write(f'Trucks updated: {updated_trucks_count}')
        self.stdout.write(f'Rows skipped: {skipped_rows}')
        self.stdout.write(self.style.SUCCESS('--- Import finished ---'))