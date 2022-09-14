from django.db import models
from django.urls import reverse
from .managers import DiscordUserOAuth2Manager


# Create your models here.
class Reminder(models.Model):
    """
    Reminders are created either on this web app, an API connection or a bot on a messaging platform.
    We at least need to know the time, message, recipient, timezone and completed.
    If routine is True, all other fields besides objects will be required.
    """
    time = models.DateTimeField()  # When the reminder should trigger
    message = models.CharField(max_length=1024)  # What the reminder should say
    recipient = models.BigIntegerField()  # Who should get the reminder (Discord User ID)
    completed = models.BooleanField()  # Has the reminder been sent?
    routine = models.BooleanField()  # Does the reminder reoccur on a schedule?
    start_date = models.DateTimeField(null=True)  # When do the reoccurrences start?
    routine_days = models.IntegerField(null=True)  # On what days does the reminder trigger?
    routine_amount = models.IntegerField(null=True)  # The reminder reoccurs X Y (3 days or 19 weeks, etc) This is X.
    routine_unit = models.CharField(max_length=20, null=True)  # This is Y from the routine_amount comment.
    end_date = models.DateTimeField(null=True)  # When should the reminder stop reoccurring?
    timezone = models.CharField(max_length=100, default="US/Central")  # In what timezone should all datetimes be read?
    objects = models.Manager()  # Internal django use. Used to get, save, update, etc Reminders.

    def get_absolute_url(self):
        """
        Useful for getting a URL that allows you to edit or view each object. In this case, it's edit.
        :return: URL
        """
        return reverse("edit_reminder") + f"?id={self.pk}"


class DiscordUser(models.Model):
    """
    Represents a logged-in Discord user. Attributes are supplied from Discord's OAuth2 endpoint.
    """
    id = models.BigIntegerField(primary_key=True)  # Most important one. We use this to see which Reminders they own.
    username = models.CharField(max_length=50)  # Useful for showing the user their name without the ID.
    # Attributes from this point on are unused.
    avatar = models.CharField(max_length=100)
    public_flags = models.IntegerField()
    flags = models.IntegerField()
    locale = models.CharField(max_length=50)
    mfa_enabled = models.BooleanField()
    discord_tag = models.CharField(max_length=50)
    last_login = models.DateTimeField()
    objects = DiscordUserOAuth2Manager()

    @staticmethod
    def is_authenticated():
        return True  # See django docs on authentication
