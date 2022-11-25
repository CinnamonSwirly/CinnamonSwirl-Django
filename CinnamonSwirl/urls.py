from django.urls import path
from CinnamonSwirl import views

# See django docs on URLs
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('reminder', views.ReminderView.as_view(), name='reminder'),
    path('logout', views.logout, name='logout'),
    path('oauth/discord_login', views.discord_login, name='discord_login'),
    path('oauth/redirect', views.discord_login_redirect, name='discord_login_redirect'),
    path('forget', views.forget, name='forget')
]
