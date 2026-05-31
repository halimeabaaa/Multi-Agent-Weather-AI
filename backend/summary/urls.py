# summary/urls.py
from django.urls import path
from .views import get_daily_summary, get_summary_history, admin_dashboard_stats
from .views import admin_create_notification, get_user_notifications
from .views import admin_get_unique_filters, admin_list_notifications, admin_delete_notification


urlpatterns = [
    path('daily/', get_daily_summary, name='daily_summary'),
    path('history/', get_summary_history, name='summary-history'),
    path('admin-stats/', admin_dashboard_stats, name='admin-stats'),
    path('notifications/create/', admin_create_notification, name='admin-create-notification'),
    path('notifications/my/', get_user_notifications, name='get-user-notifications'),
    path('notifications/all/', admin_list_notifications, name='admin-list-notifications'),
    path('notifications/<int:notification_id>/delete/', admin_delete_notification, name='admin-delete-notification'),
    path('notifications/filters/', admin_get_unique_filters, name='admin-get-unique-filters'),
]