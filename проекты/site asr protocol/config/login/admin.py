from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, UserActivity


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = (
        "login",
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_activity_datetime",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("login",)
    ordering = ("login",)
    readonly_fields = ("last_activity_datetime",)
    fieldsets = (
        (None, {"fields": ("login", "password")}),
        ("Персональные данные", {"fields": ("role", "last_activity_datetime")} ),
        (
            "Права доступа",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Важные даты", {"fields": ("last_login",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("login", "password1", "password2", "role", "is_active", "is_staff"),
        }),
    )
    filter_horizontal = ("groups", "user_permissions")


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "activity_datetime")
    list_filter = ("activity_datetime",)
    search_fields = ("user__login", "action")
