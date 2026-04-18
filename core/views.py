from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BookingForm, RegisterForm
from .logging_utils import log_action
from .models import ActionLog, Booking, Resource, UserProfile
from .utils import PAIR_SLOTS


def home(request):
    return render(request, 'home.html')


def resource_list(request):
    resources = Resource.objects.filter(is_active=True)

    search_query = request.GET.get('q', '').strip()
    selected_type = request.GET.get('type', '').strip()
    selected_department = request.GET.get('department', '').strip()
    selected_min_capacity = request.GET.get('min_capacity', '').strip()

    if search_query:
        resources = resources.filter(
            Q(name__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    if selected_type:
        resources = resources.filter(resource_type=selected_type)

    if selected_department:
        resources = resources.filter(department=selected_department)

    if selected_min_capacity:
        try:
            resources = resources.filter(capacity__gte=int(selected_min_capacity))
        except ValueError:
            selected_min_capacity = ''

    resources = list(resources)

    booking_counts = {}
    preferred_department = None

    if request.user.is_authenticated:
        from django.db.models import Count

        user_bookings = (
            Booking.objects
            .filter(user=request.user)
            .values('resource')
            .annotate(total=Count('id'))
        )

        for item in user_bookings:
            booking_counts[item['resource']] = item['total']

        if hasattr(request.user, 'profile') and request.user.profile.role == 'teacher':
            email = (request.user.email or '').lower()

            if email.endswith('@ipz.duikt.edu.ua'):
                preferred_department = 'ipz'
            elif email.endswith('@kn.duikt.edu.ua'):
                preferred_department = 'kn'
            elif email.endswith('@ai.duikt.edu.ua'):
                preferred_department = 'ai'
            elif email.endswith('@ist.duikt.edu.ua'):
                preferred_department = 'ist'

    for resource in resources:
        resource.user_booking_count = booking_counts.get(resource.id, 0)
        resource.is_recommended = resource.user_booking_count > 0
        resource.department_priority = 1 if preferred_department and resource.department == preferred_department else 0

    resources.sort(
        key=lambda r: (
            -r.department_priority,
            -r.user_booking_count,
            r.name.lower()
        )
    )

    resource_count = len(resources)

    context = {
        'resources': resources,
        'search_query': search_query,
        'selected_type': selected_type,
        'selected_department': selected_department,
        'selected_min_capacity': selected_min_capacity,
        'resource_type_choices': Resource.RESOURCE_TYPE_CHOICES,
        'department_choices': Resource.DEPARTMENT_CHOICES,
        'resource_count': resource_count,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'partials/resource_cards_partial.html', context)

    return render(request, 'resource_list.html', context)


def resource_detail(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id, is_active=True)
    return render(request, 'resource_detail.html', {'resource': resource})


def get_available_alternatives(resource, start_dt, end_dt):
    return Resource.objects.filter(
        is_active=True,
        resource_type=resource.resource_type
    ).exclude(
        id=resource.id
    ).exclude(
        bookings__status__in=['pending', 'approved'],
        bookings__start_time__lt=end_dt,
        bookings__end_time__gt=start_dt
    ).distinct().order_by('name')


@login_required
def create_booking(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id, is_active=True)
    alternative_resources = []

    if not (request.user.is_superuser or request.user.is_staff):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
            messages.error(
                request,
                'Створення бронювання доступне лише викладачам та працівникам навчального закладу.'
            )
            return redirect('resource_detail', resource_id=resource.id)

    if request.method == 'POST':
        form = BookingForm(request.POST, initial={'resource': resource})

        if form.is_valid():
            booking = form.save(commit=False)
            booking.resource = resource
            booking.user = request.user

            if resource.resource_type == 'conference_room':
                booking.status = 'pending'
                success_message = 'Бронювання успішно створено та очікує підтвердження адміністратора.'
            else:
                booking.status = 'approved'
                success_message = 'Бронювання успішно створено та автоматично підтверджено.'

            booking.save()

            log_action(
                user=request.user,
                action_type='create_booking',
                object_type='booking',
                object_repr=f'{resource.name} | {booking.start_time:%d.%m.%Y %H:%M} - {booking.end_time:%H:%M}',
                description=f'Створено бронювання ресурсу "{resource.name}" користувачем {request.user.username}.'
            )

            messages.success(request, success_message)
            return redirect('my_bookings')

        start_time = form.data.get('start_time')
        end_time = form.data.get('end_time')

        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)

                if timezone.is_naive(start_dt):
                    start_dt = timezone.make_aware(start_dt)

                if timezone.is_naive(end_dt):
                    end_dt = timezone.make_aware(end_dt)

                alternative_resources = list(
                    get_available_alternatives(resource, start_dt, end_dt)
                )

            except ValueError:
                pass
    else:
        form = BookingForm(initial={'resource': resource})

    return render(request, 'create_booking.html', {
        'resource': resource,
        'form': form,
        'alternative_resources': alternative_resources,
    })


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            UserProfile.objects.create(
                user=user,
                role=form.get_role_by_email()
            )

            messages.success(
                request,
                'Акаунт успішно створено. Після підтвердження адміністратором ви зможете увійти в систему.'
            )
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def my_bookings(request):
    now = timezone.now()

    bookings = list(
        Booking.objects.filter(user=request.user)
        .select_related('resource')
        .order_by('-start_time')
    )

    for booking in bookings:
        booking.display_status = booking.status
        booking.sort_priority = 0

        if booking.status == 'approved' and booking.end_time < now:
            booking.display_status = 'completed'
            booking.sort_priority = 1
        elif booking.status == 'cancelled':
            booking.sort_priority = 2
        elif booking.status == 'rejected':
            booking.sort_priority = 3
        else:
            booking.sort_priority = 0

    bookings.sort(key=lambda b: (b.sort_priority, -b.start_time.timestamp()))

    return render(request, 'my_bookings.html', {'bookings': bookings})

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status in ['pending', 'approved']:
        booking.status = 'cancelled'
        booking.save()

        log_action(
            user=request.user,
            action_type='cancel_booking',
            object_type='booking',
            object_repr=f'{booking.resource.name} | {booking.start_time:%d.%m.%Y %H:%M} - {booking.end_time:%H:%M}',
            description=f'Користувач {request.user.username} скасував бронювання ресурсу "{booking.resource.name}".'
        )

        messages.success(request, 'Бронювання успішно скасовано.')
    else:
        messages.warning(request, 'Це бронювання не можна скасувати.')

    return redirect('my_bookings')


@login_required
def delete_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    log_action(
        user=request.user,
        action_type='delete_booking',
        object_type='booking',
        object_repr=f'{booking.resource.name} | {booking.start_time:%d.%m.%Y %H:%M} - {booking.end_time:%H:%M}',
        description=f'Користувач {request.user.username} видалив бронювання ресурсу "{booking.resource.name}".'
    )

    booking.delete()
    messages.success(request, 'Бронювання успішно видалено.')
    return redirect('my_bookings')

@login_required
def delete_inactive_bookings(request):
    now = timezone.now()

    inactive_bookings = Booking.objects.filter(
        user=request.user
    ).filter(
        Q(status='cancelled') |
        Q(status='approved', end_time__lt=now)
    )

    count = inactive_bookings.count()

    if count == 0:
        messages.warning(request, 'У вас немає завершених або скасованих бронювань для видалення.')
        return redirect('my_bookings')

    for booking in inactive_bookings.select_related('resource'):
        log_action(
            user=request.user,
            action_type='delete_booking',
            object_type='booking',
            object_repr=f'{booking.resource.name} | {booking.start_time:%d.%m.%Y %H:%M} - {booking.end_time:%H:%M}',
            description=f'Користувач {request.user.username} видалив неактивне бронювання ресурсу "{booking.resource.name}".'
        )

    inactive_bookings.delete()
    messages.success(request, f'Успішно видалено {count} завершених/скасованих бронювань.')
    return redirect('my_bookings')

def resource_schedule(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id, is_active=True)

    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    day_start = timezone.make_aware(datetime.combine(selected_date, time(8, 0)))
    day_end = timezone.make_aware(datetime.combine(selected_date, time(20, 0)))

    bookings = Booking.objects.filter(
        resource=resource,
        status__in=['pending', 'approved'],
        start_time__lt=day_end,
        end_time__gt=day_start
    ).select_related('user').order_by('start_time')

    pair_slots = []

    for pair in PAIR_SLOTS:
        slot_start = timezone.make_aware(datetime.combine(selected_date, pair['start']))
        slot_end = timezone.make_aware(datetime.combine(selected_date, pair['end']))

        slot_booking = None
        occupancy_percent = 0
        alternatives = []

        slot_duration_seconds = (slot_end - slot_start).total_seconds()

        for booking in bookings:
            overlap_start = max(slot_start, booking.start_time)
            overlap_end = min(slot_end, booking.end_time)

            if overlap_start < overlap_end:
                slot_booking = booking
                overlap_seconds = (overlap_end - overlap_start).total_seconds()
                occupancy_percent = int((overlap_seconds / slot_duration_seconds) * 100)
                break

        if slot_booking:
            alternatives = get_available_alternatives(resource, slot_start, slot_end)

        pair_slots.append({
            'number': pair['number'],
            'start': slot_start,
            'end': slot_end,
            'booking': slot_booking,
            'is_free': slot_booking is None,
            'occupancy_percent': occupancy_percent,
            'alternatives': alternatives,
        })

    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    return render(request, 'resource_schedule.html', {
        'resource': resource,
        'selected_date': selected_date,
        'pair_slots': pair_slots,
        'prev_date': prev_date,
        'next_date': next_date,
    })


def resource_week_schedule(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id, is_active=True)

    date_str = request.GET.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    today = timezone.localdate()
    now = timezone.now()

    week_start = selected_date - timedelta(days=selected_date.weekday())
    week_dates = [week_start + timedelta(days=i) for i in range(7)]

    schedule_rows = []

    for pair in PAIR_SLOTS:
        row = {
            'pair_number': pair['number'],
            'time_range': f"{pair['start'].strftime('%H:%M')} - {pair['end'].strftime('%H:%M')}",
            'days': [],
        }

        for current_date in week_dates:
            slot_start = timezone.make_aware(datetime.combine(current_date, pair['start']))
            slot_end = timezone.make_aware(datetime.combine(current_date, pair['end']))

            booking = Booking.objects.filter(
                resource=resource,
                status__in=['pending', 'approved'],
                start_time__lt=slot_end,
                end_time__gt=slot_start
            ).select_related('user').order_by('start_time').first()

            alternatives = []
            if booking:
                alternatives = get_available_alternatives(resource, slot_start, slot_end)

            is_past = current_date < today or slot_end <= now

            row['days'].append({
                'date': current_date,
                'booking': booking,
                'is_free': booking is None,
                'slot_start': slot_start,
                'slot_end': slot_end,
                'alternatives': alternatives,
                'is_past': is_past,
            })

        schedule_rows.append(row)

    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    return render(request, 'resource_week_schedule.html', {
        'resource': resource,
        'week_dates': week_dates,
        'schedule_rows': schedule_rows,
        'week_start': week_start,
        'prev_week': prev_week,
        'next_week': next_week,
    })


@login_required
def quick_book_pair(request, resource_id, pair_number):
    resource = get_object_or_404(Resource, id=resource_id, is_active=True)

    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'message': 'Метод POST обов’язковий.'},
            status=405
        )

    if not (request.user.is_superuser or request.user.is_staff):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'teacher':
            return JsonResponse({
                'success': False,
                'message': 'Швидке бронювання доступне лише викладачам.'
            }, status=403)

    date_str = request.POST.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Невірний формат дати.'
            }, status=400)
    else:
        selected_date = timezone.localdate()

    selected_pair = next((pair for pair in PAIR_SLOTS if pair['number'] == pair_number), None)

    if not selected_pair:
        return JsonResponse({
            'success': False,
            'message': 'Невірно обрано пару.'
        }, status=400)

    start_dt = timezone.make_aware(datetime.combine(selected_date, selected_pair['start']))
    end_dt = timezone.make_aware(datetime.combine(selected_date, selected_pair['end']))

    conflict_exists = Booking.objects.filter(
        resource=resource,
        status__in=['pending', 'approved'],
        start_time__lt=end_dt,
        end_time__gt=start_dt
    ).exists()

    if conflict_exists:
        alternatives = get_available_alternatives(resource, start_dt, end_dt)

        return JsonResponse({
            'success': False,
            'message': 'Ця пара вже зайнята для обраного ресурсу.',
            'alternatives': [
                {
                    'id': alt.id,
                    'name': alt.name,
                }
                for alt in alternatives
            ]
        }, status=400)

    if resource.resource_type == 'conference_room':
        status = 'pending'
        status_label = 'Очікує підтвердження'
        message = f'Заявку на бронювання пари {pair_number} створено та передано на підтвердження.'
    else:
        status = 'approved'
        status_label = 'Зайнято'
        message = f'Пару {pair_number} успішно заброньовано та автоматично підтверджено.'

    booking = Booking.objects.create(
        resource=resource,
        user=request.user,
        start_time=start_dt,
        end_time=end_dt,
        status=status
    )

    log_action(
        user=request.user,
        action_type='create_booking',
        object_type='booking',
        object_repr=f'{resource.name} | {booking.start_time:%d.%m.%Y %H:%M} - {booking.end_time:%H:%M}',
        description=f'Швидке бронювання пари {pair_number} для ресурсу "{resource.name}" користувачем {request.user.username}.'
    )

    return JsonResponse({
        'success': True,
        'message': message,
        'booking': {
            'id': booking.id,
            'status': booking.status,
            'status_label': status_label,
            'username': request.user.username,
            'start_time': booking.start_time.strftime('%H:%M'),
            'end_time': booking.end_time.strftime('%H:%M'),
        }
    })


@staff_member_required
def admin_pending_bookings(request):
    bookings = Booking.objects.select_related('resource', 'user').filter(status='pending').order_by('start_time')
    return render(request, 'admin_pending_bookings.html', {'bookings': bookings})


@staff_member_required
def approve_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != 'pending':
        messages.warning(request, 'Підтвердити можна лише бронювання зі статусом "Очікує підтвердження".')
        return redirect('admin_pending_bookings')

    booking.status = 'approved'
    booking.save(update_fields=['status'])

    log_action(
        user=request.user,
        action_type='approve_booking',
        object_type='booking',
        object_repr=f'{booking.resource.name} | {booking.start_time:%d.%m.%Y %H:%M} - {booking.end_time:%H:%M}',
        description=f'Адміністратор {request.user.username} підтвердив бронювання користувача {booking.user.username}.'
    )

    messages.success(request, 'Бронювання підтверджено.')
    return redirect('admin_pending_bookings')


@staff_member_required
def reject_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != 'pending':
        messages.warning(request, 'Відхилити можна лише бронювання зі статусом "Очікує підтвердження".')
        return redirect('admin_pending_bookings')

    booking.status = 'rejected'
    booking.save(update_fields=['status'])

    log_action(
        user=request.user,
        action_type='reject_booking',
        object_type='booking',
        object_repr=f'{booking.resource.name} | {booking.start_time:%d.%m.%Y %H:%M} - {booking.end_time:%H:%M}',
        description=f'Адміністратор {request.user.username} відхилив бронювання користувача {booking.user.username}.'
    )

    messages.success(request, 'Бронювання відхилено.')
    return redirect('admin_pending_bookings')


@staff_member_required
def action_logs(request):
    logs = ActionLog.objects.select_related('user').all()[:300]
    return render(request, 'action_logs.html', {'logs': logs})