from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .logging_utils import log_action


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    log_action(
        user=user,
        action_type='login',
        object_type='auth',
        object_repr='Вхід у систему',
        description=f'Користувач {user.username} увійшов у систему.'
    )


@receiver(user_logged_out)
def handle_user_logged_out(sender, request, user, **kwargs):
    if user:
        log_action(
            user=user,
            action_type='logout',
            object_type='auth',
            object_repr='Вихід із системи',
            description=f'Користувач {user.username} вийшов із системи.'
        )