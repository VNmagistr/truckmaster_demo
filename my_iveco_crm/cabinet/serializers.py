import re
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from clients.models import Client
from orders.models import ServiceOrder, ServiceWork, RepairPhoto
from clients.models import Truck


# ── Client login token ──────────────────────────────────────────────────────

class ClientTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login для клієнта: перевіряє, що user має client_profile."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_client'] = True
        token['client_id'] = user.client_profile.id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        if not hasattr(self.user, 'client_profile'):
            raise serializers.ValidationError(
                "Акаунт не пов'язаний з профілем клієнта."
            )

        client = self.user.client_profile
        data['user'] = {
            'id': self.user.id,
            'client_id': client.id,
            'name': client.name,
            'phone': client.phone,
            'is_client': True,
        }
        return data


# ── Client registration ──────────────────────────────────────────────────────

class ClientRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=6, write_only=True)

    def validate_phone(self, value):
        normalized = re.sub(r'[^\d+]', '', value)
        if len(normalized) < 10:
            raise serializers.ValidationError("Невірний формат номера телефону.")
        return normalized

    def validate(self, data):
        phone = data['phone']
        if User.objects.filter(username=phone).exists():
            raise serializers.ValidationError(
                {"phone": "Акаунт з цим номером телефону вже існує."}
            )
        # Перевіряємо чи клієнт вже має прив'язаний акаунт
        existing_client = Client.objects.filter(phone=phone).first()
        if existing_client and existing_client.user_id:
            raise serializers.ValidationError(
                {"phone": "Клієнт з цим номером вже має акаунт."}
            )
        return data

    def create(self, validated_data):
        phone = validated_data['phone']
        name = validated_data['name']
        password = validated_data['password']

        # Знаходимо існуючого клієнта або створюємо нового
        client = Client.objects.filter(phone=phone).first()
        if client is None:
            client = Client.objects.create(name=name, phone=phone)

        user = User.objects.create_user(username=phone, password=password)
        client.user = user
        client.save(update_fields=['user'])
        return user


# ── Cabinet read serializers ─────────────────────────────────────────────────

class CabinetClientSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()

    def get_features(self, obj):
        try:
            f = obj.features
            return {
                'cabinet':                f.cabinet,
                'bot':                    f.bot,
                'invoices':               f.invoices,
                'appointments':           f.appointments,
                'notifications_telegram': f.notifications_telegram,
                'notifications_whatsapp': f.notifications_whatsapp,
            }
        except Exception:
            return {
                'cabinet': True, 'bot': True, 'invoices': True,
                'appointments': True, 'notifications_telegram': True,
                'notifications_whatsapp': True,
            }

    class Meta:
        model = Client
        fields = ['id', 'name', 'phone', 'email', 'address', 'features']


class CabinetTruckSerializer(serializers.ModelSerializer):
    base_model = serializers.StringRelatedField()
    euro_standard_display = serializers.CharField(
        source='get_euro_standard_display', read_only=True
    )
    latest_mileage = serializers.SerializerMethodField()

    def get_latest_mileage(self, obj):
        return obj.get_latest_mileage()

    class Meta:
        model = Truck
        fields = [
            'id', 'base_model', 'specific_model_name',
            'license_plate', 'last_seven_vin',
            'euro_standard', 'euro_standard_display',
            'latest_mileage',
        ]


class CabinetRepairPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairPhoto
        fields = ['id', 'image', 'description']


class CabinetServiceWorkSerializer(serializers.ModelSerializer):
    work_name = serializers.SerializerMethodField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    def get_work_name(self, obj):
        return obj.work.name if obj.work else obj.description

    class Meta:
        model = ServiceWork
        fields = ['id', 'work_name', 'description', 'hours_spent', 'price_at_moment', 'amount']


class CabinetOrderListSerializer(serializers.ModelSerializer):
    truck = CabinetTruckSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_number', 'truck', 'status', 'status_display',
            'total_cost', 'created_at', 'problem_description',
        ]


class CabinetOrderDetailSerializer(serializers.ModelSerializer):
    truck = CabinetTruckSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    works = CabinetServiceWorkSerializer(many=True, read_only=True)
    photos = CabinetRepairPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceOrder
        fields = [
            'id', 'order_number', 'truck', 'status', 'status_display',
            'total_cost', 'created_at', 'updated_at',
            'problem_description', 'recommendations', 'current_mileage',
            'works', 'photos',
        ]
