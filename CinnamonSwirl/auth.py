from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import ObjectDoesNotExist
from .models import DiscordUser


class DiscordAuthenticationBackend(BaseBackend):
    """
    | The standard django authentication backend tries to verify an account using their username, but in this case,
        we want to use their discord ID.
    | See: https://docs.djangoproject.com/en/4.1/topics/auth/
    """
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
        except ObjectDoesNotExist:
            return None
