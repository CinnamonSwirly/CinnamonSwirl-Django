import discord
import requests
from App import settings


def send_webhook_message(message):
    with requests.Session() as session:
        webhook = discord.SyncWebhook.from_url(settings.DISCORD_WEBHOOK_URL, session=session)
        webhook.send(message, username='CinnamonSwirl Backend')


def send_test_message_signal(discord_user_id):
    message = f"test:{discord_user_id}"
    send_webhook_message(message)
    return True


def send_channel_creation_signal(discord_user_id):
    message = f"channel:{discord_user_id}"
    send_webhook_message(message)
    return True
