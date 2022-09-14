from django.urls import path
from CinnamonSwirl import views

# See django docs on URLs
urlpatterns = [
    path('', views.list_reminders, name='home'),
    path('reminders/new', views.create_reminder, name='create_reminder'),
    path('reminders/list', views.list_reminders, name='get_reminders'),
    path('reminders/edit', views.edit_reminder, name='edit_reminder'),
    path('reminders/delete', views.delete_reminder, name='delete_reminder'),
    path('oauth/discord_login', views.discord_login, name='discord_login'),
    path('oauth/redirect', views.discord_login_redirect, name='discord_login_redirect')
]
