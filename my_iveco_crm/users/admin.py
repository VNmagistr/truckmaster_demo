from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'Профіль'
    verbose_name_plural = 'Профіль'
    fields = ('role', 'phone', 'position')


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff')
    list_filter = BaseUserAdmin.list_filter + ('profile__role',)

    @admin.display(description='Роль', ordering='profile__role')
    def get_role(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_role_display()
        return '-'


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
