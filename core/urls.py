from django.urls import path
from .views import (
    home,
    resource_list,
    resource_detail,
    create_booking,
    register_view,
    my_bookings,
    cancel_booking,
    delete_booking,
    delete_inactive_bookings,
    resource_schedule,
    resource_week_schedule,
    quick_book_pair,
    admin_pending_bookings,
    approve_booking,
    reject_booking,
    action_logs,
)

urlpatterns = [
    path('', home, name='home'),

    path('resources/', resource_list, name='resource_list'),
    path('resources/<int:resource_id>/', resource_detail, name='resource_detail'),
    path('resources/<int:resource_id>/book/', create_booking, name='create_booking'),
    path('resources/<int:resource_id>/schedule/', resource_schedule, name='resource_schedule'),
    path('resources/<int:resource_id>/week/', resource_week_schedule, name='resource_week_schedule'),
    path('resources/<int:resource_id>/quick-book/<int:pair_number>/', quick_book_pair, name='quick_book_pair'),

    path('accounts/register/', register_view, name='register'),

    path('my-bookings/', my_bookings, name='my_bookings'),
    path('my-bookings/<int:booking_id>/cancel/', cancel_booking, name='cancel_booking'),
    path('my-bookings/<int:booking_id>/delete/', delete_booking, name='delete_booking'),
    path('my-bookings/delete-inactive/', delete_inactive_bookings, name='delete_inactive_bookings'),

    path('logs/', action_logs, name='action_logs'),

    path('dashboard/pending-bookings/', admin_pending_bookings, name='admin_pending_bookings'),
    path('dashboard/pending-bookings/<int:booking_id>/approve/', approve_booking, name='approve_booking'),
    path('dashboard/pending-bookings/<int:booking_id>/reject/', reject_booking, name='reject_booking'),
]