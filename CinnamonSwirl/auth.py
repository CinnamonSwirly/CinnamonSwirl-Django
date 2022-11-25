from django.contrib.auth.backends import BaseBackend
from .models import DiscordUser


class DiscordAuthenticationBackend(BaseBackend):
    def authenticate(self, request, user=None):
        find_user = DiscordUser.objects.filter(id=user['id'])
        if len(find_user) == 0:
            new_user = DiscordUser.objects.create_user(user=user)
            return new_user
        else:
            return find_user[0]

    def get_user(self, user_id):
        try:
            return DiscordUser.objects.get(pk=user_id)
        except DiscordUser.objects.ObjectDoesNotExist:
            return None
