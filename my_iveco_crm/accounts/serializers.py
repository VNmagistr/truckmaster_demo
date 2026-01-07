# accounts/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Додаємо інформацію про користувача
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }
        
        # Додаємо роль з UserProfile (якщо є)
        if hasattr(self.user, 'profile'):
            data['user']['role'] = self.user.profile.role
            data['user']['position'] = self.user.profile.position
        else:
            # Якщо профілю немає, перевіряємо чи це superuser
            if self.user.is_superuser:
                data['user']['role'] = 'admin'
            else:
                data['user']['role'] = 'mechanic'  # За замовчуванням
        
        return data

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user
