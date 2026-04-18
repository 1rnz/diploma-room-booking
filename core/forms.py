from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Booking


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['start_time', 'end_time']
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
            'end_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-control'}
            ),
        }
        labels = {
            'start_time': 'Початок бронювання',
            'end_time': 'Кінець бронювання',
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise forms.ValidationError('Час завершення має бути пізніше за час початку.')

            resource = self.initial.get('resource')

            if resource:
                conflicts = Booking.objects.filter(
                    resource=resource,
                    status__in=['pending', 'approved'],
                    start_time__lt=end_time,
                    end_time__gt=start_time
                )

                if conflicts.exists():
                    raise forms.ValidationError(
                        'Цей ресурс вже заброньований у вказаний час.'
                    )

        return cleaned_data


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label='Корпоративна електронна пошта',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        label="Ім'я користувача",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Підтвердження пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    STUDENT_DOMAIN = 'stud.duikt.edu.ua'
    TEACHER_DOMAIN = 'duikt.edu.ua'

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email'].lower().strip()

        try:
            domain = email.split('@')[1]
        except IndexError:
            raise forms.ValidationError('Невірний формат електронної пошти.')

        if domain not in [self.STUDENT_DOMAIN, self.TEACHER_DOMAIN]:
            raise forms.ValidationError(
                f'Реєстрація дозволена лише для адрес доменів @{self.STUDENT_DOMAIN} або @{self.TEACHER_DOMAIN}.'
            )

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Користувач з такою електронною поштою вже існує.')

        return email

    def get_role_by_email(self):
        email = self.cleaned_data['email'].lower().strip()
        domain = email.split('@')[1]

        if domain == self.STUDENT_DOMAIN:
            return 'student'
        return 'teacher'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.is_active = False

        if commit:
            user.save()

        return user