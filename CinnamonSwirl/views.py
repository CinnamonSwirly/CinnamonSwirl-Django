from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Iterable
from configparser import ConfigParser
from pathlib import Path

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from requests import post as requests_post, get as requests_get

from CinnamonSwirl import filters
from CinnamonSwirl import forms
from CinnamonSwirl import models
from CinnamonSwirl import tables

from App import settings

BASE_DIR = Path(__file__).resolve().parent.parent
configuration = ConfigParser()
configuration.read(f"{BASE_DIR}\\config.cfg")

# Provided by Discord's OAuth2 URL Generator in your application's OAuth2 settings. Note the scope must be changed if
#  further permissions are desired.
auth_url = settings.DISCORD_AUTH_URL


@login_required(login_url="oauth/discord_login")
@require_http_methods(["GET"])
def list_reminders(request):
    """
    Renders a table of the current reminders for the logged-in user. Uses django_filters and django_tables2 to generate
    the table and filter the data shown.
    :param request: No requirements.
    :return: HTTPResponse
    """
    filtered_data = filters.RemindersFilter(request=request, queryset=models.Reminder.objects.all())
    # Actual results of the filter is found as filtered_data.qs, not .data as that dumps the raw input of the filter.
    table = tables.RemindersTable(data=filtered_data.qs, empty_text="You currently have no reminders!")
    return render(request, 'get_reminders.html', {'table': table, 'CreateButtonForm': forms.CreateButtonForm})


@login_required(login_url="oauth/discord_login")
@require_http_methods(["GET", "POST"])
def create_reminder(request):
    """
    Offers a form for users to create a reminder. When POSTing, it attempts to validate and commit the reminder if OK.
    :param request: GET has no requirements. POST must have relevant attributes for a reminder. See models.
    :return: HTTPResponse
    """
    message = ''

    if request.method == 'POST':
        try:
            parse_reminder(request=request)
            return redirect("get_reminders")
        except ValueError:
            message = 'One or more values were not understood. Please try again.'
        except AssertionError:
            message = 'One or more required values were missing. Please check your input and try again.'
        except ValidationError:
            message = "One or more dates or times were invalid. Please check your input and try again."

        request.session['timezone'] = request.POST.get('timezone')

    form = forms.ReminderForm(request=request)
    return render(request, 'create_reminder.html', {'ReminderForm': form, 'message': message})


@login_required(login_url="oauth/discord_login")
@require_http_methods(["GET", "POST"])
def edit_reminder(request):
    """
    Offers a form to view and edit the details for the provided reminder ID. Will make sure the reminder belongs to the
    logged-in user by comparing recipient ID. Returns 403 if this lookup fails. Also offers a way to delete reminders.
    When POSTing, this attempts to validate the edits and commit them.
    :param request: GET must have an 'id' attribute. POST must have relevant attributes for a reminder. See models.
    :return: HTTPResponse
    """
    if request.method == 'POST':
        reminder_id = request.POST.get("reminder_id")
    else:
        reminder_id = request.GET.get("id")

    try:
        reminder = models.Reminder.objects.get(pk=reminder_id, recipient=request.user.id)
    except ObjectDoesNotExist:
        return HttpResponseForbidden()

    message = "You are editing a reminder."

    if request.method == 'POST':
        try:
            parse_reminder(request)
            return redirect("get_reminders")
        except AssertionError:
            message = "One or more required fields was empty. Please try your edit again."
        except ValueError:
            message = "One or more fields was invalid. Please check your input and try again."
        except ValidationError:
            message = "One or more dates or times were invalid. Please check your input and try again."

    form = forms.ReminderForm(request=request, reminder=reminder)
    delete_form = forms.DeleteConfirmationForm(reminder=reminder)
    return render(request, 'edit_reminder.html', {'ReminderForm': form, 'DeleteConfirmationForm': delete_form,
                                                  'message': message})


@login_required(login_url="oauth/discord_login")
@require_http_methods(["POST"])
def delete_reminder(request):
    """
    Validates that the logged-in user owns the supplied reminder ID by verifying recipient ID. If a match is found,
    deletes the object from the DB. Returns 403 if this lookup fails.
    :param request: Must have a 'reminder_id' attribute
    :return: HTTPRedirect
    """
    if not request.POST.get("reminder_id"):
        return HttpResponseForbidden()

    try:
        reminder = models.Reminder.objects.get(pk=request.POST.get("reminder_id"), recipient=request.user.id)
    except ObjectDoesNotExist:
        return HttpResponseForbidden()

    if reminder:
        reminder.delete()

    return redirect("get_reminders")


@require_http_methods(["GET"])
def discord_login(request: HttpRequest):
    """
    Sends the user to Discord's OAuth endpoint to do their thing.
    :param request: No requirements.
    :return: HTTPRedirect
    """
    if request:
        return redirect(auth_url)


@require_http_methods(["GET"])
def discord_login_redirect(request: HttpRequest):
    """
    Receives the user back from discord_login. Hopefully they have been given all they need from Discord.
    Gets a token from discord with the authorization code received.
    Leverages django's built-in authentication from here. See auth, models, and managers.
    :param request: Must contain a 'code' attribute.
    :return: HTTPRedirect
    """
    code = request.GET.get('code')
    user = exchange_code(code)
    discord_user = authenticate(request, user=user)
    login(request, discord_user)
    return redirect('get_reminders')


# TODO: This can be used to refresh the token, but currently that's not implemented. Users have to re-authorize after
#  a time. This can be set up at any time if you follow the discord OAuth docs.
def exchange_code(code: str):
    """
    Usual setup for getting an access token through OAuth2. We give discord a code, ask for the same scope we presented
    the user and in return we get an access token.
    :param code: Provided by discord_login_redirect
    :return: JSON back from Discord's OAuth2 endpoint
    """
    data = {
        'client_id': settings.DISCORD_CLIENT_ID,
        'client_secret': settings.DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.DISCORD_REDIRECT_URI,
        'scope': 'identify'
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests_post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    credentials = response.json()
    access_token = credentials['access_token']
    response = requests_get('https://discord.com/api/v10/users/@me', headers={
        'Authorization': f'Bearer {access_token}'
    })
    return response.json()


def parse_reminder(request) -> bool:
    """
    Attempts to format the request attributes from create_reminder's form so they can be understood by the Reminder
    model manager.
    :raises AssertionError: If an attribute is missing
    :raises ValueError: If a date was invalid
    :param request: POST must contain relevant attributes for a reminder. See models.
    :return: models.Reminder
    """
    required_fields = ["timezone", "startDate", "startTime", "message", "timezone"]
    for field in required_fields:
        assert request.POST.get(field)

    timezone = request.POST.get('timezone')

    start_datetime = time_to_utc(date=request.POST.get('startDate'), time=request.POST.get('startTime'),
                                 timezone=timezone)

    kwargs = {"dtstart": start_datetime, "timezone": timezone, "message": request.POST.get('message'),
              "recipient": request.POST.get('recipient'), "finished": False}

    if request.POST.get('routine'):
        if request.POST.get('count'):
            kwargs.update({"count": request.POST.get('count')})

        if request.POST.get('schedule_end_date'):
            assert request.POST.get('schedule_end_time')

            schedule_end_datetime = time_to_utc(date=request.POST.get('schedule_end_date'),
                                                time=request.POST.get('schedule_end_time'), timezone=timezone)
            # Count and Until cannot coexist in datetime.rrule. We will prioritize until over count.
            kwargs.update({"until": schedule_end_datetime, "count": None})

        # For the next two blocks, we want to turn a list of strings into a string. [1, 2, 3] is the goal.
        if request.POST.get('schedule_days'):
            days = []
            for day in request.POST.getlist('schedule_days'):
                days.append(int(day))
            kwargs.update({"byweekday": str(days)})

        if request.POST.get('schedule_hours'):
            hours = []
            offset = int(datetime.utcnow().astimezone(ZoneInfo(timezone)).strftime('%z')[:3])
            for hour in request.POST.getlist('schedule_hours'):
                hours.append(int(hour) - offset)
            kwargs.update({"byhour": str(hours)})

        kwargs.update({"interval": request.POST.get('schedule_interval'), "freq": request.POST.get('schedule_units')})
    else:
        # This is how we will present a one-time reminder to dateutil.rrule
        kwargs.update({"freq": "MINUTELY", "interval": 1})

    if request.POST.get('reminder_id'):
        models.Reminder.objects.filter(pk=request.POST.get('reminder_id'), recipient=request.user.id).update(**kwargs)
        return True
    else:
        models.Reminder.objects.create(**kwargs)
        return True


def time_to_utc(date: str, time: str, timezone: str) -> datetime:
    """
    :param date: A string in format %Y-%m-%d
    :param time: A string in format %H:%M
    :param timezone: The timezone the supplied date and time are from
    :return: datetime in UTC timezone with tzinfo removed.
    """
    date_time = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M')
    time_in_local = date_time.replace(tzinfo=ZoneInfo(timezone))
    time_in_utc = time_in_local.astimezone(ZoneInfo("UTC"))
    return time_in_utc.replace(tzinfo=None)


def requires_attributes(subject, attributes: Iterable) -> bool:
    """
    :param subject: request.GET, request.POST or other relevant method
    :param attributes: Iterable of strings. Must be names of attributes contained in the subject
    :return: bool
    """
    for attribute in attributes:
        try:
            assert subject.get(attribute) is not None
        except AssertionError:
            return False
        return True


@require_http_methods(["GET"])
def home(request):
    if request.user.is_authenticated:
        return list_reminders(request)
    return render(request, "index.html", {'auth_url': auth_url})
