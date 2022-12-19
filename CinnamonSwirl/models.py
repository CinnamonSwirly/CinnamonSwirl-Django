from django.db import models
from django.urls import reverse
from .managers import DiscordUserOAuth2Manager
from django.utils.timezone import now
import re


class DiscordUser(models.Model):
    """
    | Represents a logged-in Discord user. Attributes are supplied from Discord's OAuth2 endpoint.
    | See: https://discord.com/developers/docs/topics/oauth2

    | id
    | username
    | avatar
    | public_flags
    | flags
    | locale
    | mfa_endabled
    | discord_tag
    | last_login
    | objects: django internal use, does not need to be defined on instantiation
    """
    id = models.BigIntegerField(primary_key=True)  # Most important one. We use this to see which Reminders they own.
    username = models.CharField(max_length=50)  # Useful for showing the user their name without the ID.
    # Attributes from this point on are unused.
    avatar = models.CharField(max_length=100, null=True)
    public_flags = models.IntegerField()
    flags = models.IntegerField()
    locale = models.CharField(max_length=50)
    mfa_enabled = models.BooleanField()
    discord_tag = models.CharField(max_length=50)
    last_login = models.DateTimeField()
    guild_preference = models.BooleanField(default=False)  # In the future, maybe users can invite the bot for TRUE?
    message_preference = models.BooleanField(default=False)  # False: DM, True: Channel
    setup_flags = models.IntegerField(default=0)  # 0: New, 1: Joined Server, 2: Message preference, 3: Tested OK
    in_setup = models.BooleanField(default=True)
    channel = models.BigIntegerField(null=True)
    objects = DiscordUserOAuth2Manager()

    @staticmethod
    def is_authenticated():
        return True  # See django docs on authentication


class Reminder(models.Model):
    """
    Reminders are created either on this web app, an API connection or a bot on a messaging platform.

    At minimum, you should define freq, message, recipient, and interval.
    All of these fields, except message, recipient, finished and timezone, correspond to dateutil.rrule as that will
    be run against this row to identify the next occurrence of a schedule.

    See: https://dateutil.readthedocs.io/en/stable/rrule.html

    | freq
    | message: str
    | recipient: DiscordUser ID
    | finished: bool
    | interval
    | dtstart
    | wkst
    | count
    | until
    | bysetpos
    | bymonth
    | bymonthday
    | byyearday
    | byweekno
    | byweekday
    | byhour
    | byminute
    | bysecond
    | timezone
    | objects: django internal use, does not need to be defined on instantiation
    """
    # YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY, SECONDLY
    freq = models.CharField(max_length=10, default="MINUTELY")
    message = models.CharField(max_length=1024, default="Reminder")
    recipient = models.BigIntegerField(default=0)  # Discord ID to send to
    finished = models.BooleanField(default=False)
    interval = models.IntegerField(default=1)  # How many of freq between recurrences
    dtstart = models.DateTimeField(default=now)
    wkst = models.IntegerField(null=True)
    count = models.IntegerField(null=True)
    until = models.DateTimeField(null=True)
    bysetpos = models.CharField(max_length=100, null=True)
    bymonth = models.CharField(max_length=100, null=True)
    bymonthday = models.CharField(max_length=100, null=True)
    byyearday = models.CharField(max_length=100, null=True)
    byweekno = models.CharField(max_length=100, null=True)
    byweekday = models.CharField(max_length=100, null=True)
    byhour = models.CharField(max_length=100, null=True)
    byminute = models.CharField(max_length=100, null=True)
    bysecond = models.CharField(max_length=100, null=True)
    timezone = models.CharField(max_length=100, default="US/Central")  # In what timezone should all datetimes be read?
    objects = models.Manager()  # Internal django use. Used to get, save, update, etc Reminders.

    def get_absolute_url(self):
        """
        Useful for getting a URL that allows you to edit or view each object. In this case, it's edit.
        :return: URL
        """
        return reverse("reminder") + f"?id={self.pk}"
