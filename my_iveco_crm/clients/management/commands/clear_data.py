from django.core.management.base import BaseCommand
from clients.models import Client, Truck
from orders.models import ServiceOrder

class Command(BaseCommand):
    help = 'Deletes all clients, trucks, and service orders from the database.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('This will delete ALL clients, trucks, and service orders.'))
        confirmation = input('Are you sure you want to continue? (yes/no): ')

        if confirmation.lower() == 'yes':
            # Видаляємо в правильному порядку, щоб уникнути помилок зв'язків
            ServiceOrder.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Successfully deleted all service orders.'))

            Truck.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Successfully deleted all trucks.'))

            Client.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Successfully deleted all clients.'))

            self.stdout.write(self.style.SUCCESS('All data has been cleared.'))
        else:
            self.stdout.write(self.style.NOTICE('Operation cancelled.'))