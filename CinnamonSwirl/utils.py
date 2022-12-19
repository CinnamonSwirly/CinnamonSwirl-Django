import discord
import requests
import models
from App import settings
from django.db.models import ObjectDoesNotExist


def send_webhook_message(message):
    with requests.Session() as session:
        webhook = discord.SyncWebhook.from_url(settings.DISCORD_WEBHOOK_URL, session=session)
        webhook.send(message, username='CinnamonSwirl Backend')


def send_test_message_signal(discord_user_id):
    message = f"test:{discord_user_id}"
    send_webhook_message(message)
    return True


def send_channel_creation_signal(discord_user_id):
    try:
        guild = models.DiscordUser.objects.get(pk=discord_user_id).guild
    except ObjectDoesNotExist:
        return False
    message = f"channel:{guild}"
    send_webhook_message(message)
    return True
