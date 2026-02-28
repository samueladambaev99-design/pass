from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import secrets
from django.utils import timezone
from datetime import timedelta
import random


class UserRole(models.TextChoices):
    CUSTOMER = "customer", "Обычный пользователь"
    MANAGER = "manager", "Менеджер"
    COURIER = "courier", "Курьер"

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email Not Null")
        
        email = self.normalize_email(email)
        extra_fields.setdefault("role", UserRole.CUSTOMER)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.MANAGER)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='Почта')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    telegram_chat_id = models.BigIntegerField(blank=True, null=True)

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
        verbose_name='Роль'
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @property
    def is_manager(self) -> bool:
        return self.role == UserRole.MANAGER or self.is_superuser

    @property
    def is_courier(self) -> bool:
        return self.role == UserRole.COURIER

    @property
    def is_customer(self) -> bool:
        return self.role == UserRole.CUSTOMER

    def __str__(self):
        return self.email   

class TelegramLinkCode(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name="tg_link"    
    )
    code = models.CharField(max_length=10, unique=True)
    is_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_code() -> str:
        return str(secrets.randbelow(900000) + 100000)
    
class PasswordResetCode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_codes"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))

    def __str__(self):
        return f"{self.user.email} - {self.code}"