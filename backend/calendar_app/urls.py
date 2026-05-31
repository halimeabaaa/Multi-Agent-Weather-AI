# calendar_app/urls.py
from django.urls import path
from .views import event_list_create_view, event_delete_view

urlpatterns = [
    path('events/', event_list_create_view, name='event-list-create'),
    path('events/<int:pk>/delete/', event_delete_view, name='event-delete'),
]