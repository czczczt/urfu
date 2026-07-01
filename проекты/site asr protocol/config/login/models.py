from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, login: str, password: str | None = None, **extra_fields):
        if not login:
            raise ValueError("login is required")
        user = self.model(login=login, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, login: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(login=login, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        USER = "u", "Пользователь"
        ADMIN = "a", "Администратор"
        USER_AND_ADMIN = "ua", "Пользователь+Администратор"

    login = models.CharField(max_length=150, unique=True)
    cookie = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=2, choices=Role.choices, default=Role.USER)
    last_activity_datetime = models.DateTimeField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self) -> str:
        return self.login


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity_datetime = models.DateTimeField()
    action = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Активность пользователя"
        verbose_name_plural = "История активностей пользователей"
        ordering = ["-activity_datetime"]

    def __str__(self) -> str:
        return f"{self.user.login}: {self.action}"
