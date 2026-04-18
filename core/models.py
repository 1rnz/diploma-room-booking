from django.db import models
from django.contrib.auth.models import User
from .utils import get_booking_pair_label

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('teacher', 'Викладач'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Користувач'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        verbose_name='Роль'
    )

    class Meta:
        verbose_name = 'Профіль користувача'
        verbose_name_plural = 'Профілі користувачів'

    def __str__(self):
        return f"{self.user.username} — {self.get_role_display()}"



class Resource(models.Model):
    RESOURCE_TYPE_CHOICES = [
        ('room', 'Аудиторія'),
        ('lab', 'Лабораторія'),
        ('equipment', 'Обладнання'),
        ('computer_class', 'Комп’ютерний клас'),
        ('conference_room', 'Конференц-зала'),
    ]

    DEPARTMENT_CHOICES = [
        ('ipz', 'Інженерії програмного забезпечення (ІПЗ)'),
        ('kn', 'Комп’ютерних наук (КН)'),
        ('ai', 'Штучного інтелекту (ШІ)'),
        ('ist', 'Інформаційних систем та технологій (ІСТ)'),
    ]

    name = models.CharField(max_length=255, verbose_name='Назва')
    resource_type = models.CharField(
        max_length=50,
        choices=RESOURCE_TYPE_CHOICES,
        verbose_name='Тип ресурсу'
    )
    department = models.CharField(
        max_length=20,
        choices=DEPARTMENT_CHOICES,
        blank=True,
        verbose_name='Кафедра'
    )
    description = models.TextField(blank=True, verbose_name='Опис')
    location = models.CharField(max_length=255, verbose_name='Місцезнаходження')
    capacity = models.PositiveIntegerField(default=1, verbose_name='Місткість')
    is_active = models.BooleanField(default=True, verbose_name='Активний')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')

    class Meta:
        verbose_name = 'Ресурс'
        verbose_name_plural = 'Ресурси'
        ordering = ['name']

    def __str__(self):
        return self.name

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Очікує підтвердження'),
        ('approved', 'Підтверджено'),
        ('rejected', 'Відхилено'),
        ('cancelled', 'Скасовано'),
    ]

    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Ресурс'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Користувач'
    )
    start_time = models.DateTimeField(verbose_name='Початок')
    end_time = models.DateTimeField(verbose_name='Кінець')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')

    class Meta:
        verbose_name = 'Бронювання'
        verbose_name_plural = 'Бронювання'
        ordering = ['-start_time']

    def get_pair_label(self):
        return get_booking_pair_label(self.start_time, self.end_time)
    
    def __str__(self):
        return f"{self.resource.name} ({self.start_time} - {self.end_time})"
    

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Вхід у систему'),
        ('create_booking', 'Створення бронювання'),
        ('cancel_booking', 'Скасування бронювання'),
        ('delete_booking', 'Видалення бронювання'),
        ('approve_booking', 'Підтвердження бронювання'),
        ('reject_booking', 'Відхилення бронювання'),
    ]

    OBJECT_TYPE_CHOICES = [
        ('user', 'Користувач'),
        ('resource', 'Ресурс'),
        ('booking', 'Бронювання'),
        ('system', 'Система'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Користувач'
    )
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name='Тип дії'
    )
    object_type = models.CharField(
        max_length=50,
        choices=OBJECT_TYPE_CHOICES,
        verbose_name='Тип об’єкта'
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='ID об’єкта'
    )
    description = models.TextField(verbose_name='Опис')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Час')

    class Meta:
        verbose_name = 'Лог дії'
        verbose_name_plural = 'Логи дій'
        ordering = ['-created_at']

    def __str__(self):
        username = self.user.username if self.user else 'Невідомий'
        return f"{username} — {self.get_action_type_display()} — {self.created_at:%d.%m.%Y %H:%M}"
    
from django.conf import settings


class ActionLog(models.Model):
    ACTION_CHOICES = [
        ('login', 'Вхід'),
        ('logout', 'Вихід'),
        ('create_booking', 'Створення бронювання'),
        ('cancel_booking', 'Скасування бронювання'),
        ('approve_booking', 'Підтвердження бронювання'),
        ('reject_booking', 'Відхилення бронювання'),
        ('delete_booking', 'Видалення бронювання'),
        ('create_resource', 'Створення ресурсу'),
        ('update_resource', 'Оновлення ресурсу'),
        ('delete_resource', 'Видалення ресурсу'),
        ('admin_action', 'Дія адміністратора'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Користувач'
    )
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name='Тип дії')
    object_type = models.CharField(max_length=100, blank=True, verbose_name='Тип об’єкта')
    object_repr = models.CharField(max_length=255, blank=True, verbose_name='Об’єкт')
    description = models.TextField(blank=True, verbose_name='Опис')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Час')

    class Meta:
        verbose_name = 'Лог дії'
        verbose_name_plural = 'Логи дій'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_type_display()} - {self.object_repr} - {self.created_at:%d.%m.%Y %H:%M}'