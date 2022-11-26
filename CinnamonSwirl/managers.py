from django.contrib.auth import models
from datetime import datetime


class DiscordUserOAuth2Manager(models.UserManager):
    """
    | We must override django's built-in authentication manager because we will be logging in and authenticating
        the user based on their discord user ID we received from discord's OAuth2 endpoint instead of a generic username

    See: https://docs.djangoproject.com/en/4.1/topics/auth/
    """
    def __init__(self, *args, **kwargs):
        super(DiscordUserOAuth2Manager, self).__init__(*args, **kwargs)

    def create_user(self, username=None, email=None, password=None, user=None, **extra_fields):
        new_user = self.create(
            id=user["id"],
            username=user["username"],
            avatar=user["avatar"],
            public_flags=user["public_flags"],
            flags=user["flags"],
            locale=user["locale"],
            mfa_enabled=user["mfa_enabled"],
            discord_tag=f"{user['username']}#{user['discriminator']}",
            last_login=datetime.utcnow()
        )
        return new_user
