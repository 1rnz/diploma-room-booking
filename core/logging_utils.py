from .models import ActionLog


def log_action(user=None, action_type='', object_type='', object_repr='', description=''):
    ActionLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        action_type=action_type,
        object_type=object_type,
        object_repr=object_repr,
        description=description,
    )