from datetime import datetime
from zoneinfo import ZoneInfo
from configparser import ConfigParser
from pathlib import Path

from django.views import View
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponseForbidden
from django.shortcuts import redirect, reverse
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
    model manager. If fed an existing reminder via a reminder_id parameter in the request, it will attempt to
    update that existing reminder instead of making a new one.
    :raises AssertionError: If an attribute is missing
    :raises ValueError: If a date was invalid
    :param request: POST must contain relevant attributes for a reminder. See models.
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
        count = request.POST.get('count', None)
        schedule_end_date = request.POST.get('schedule_end_date', None)
        schedule_end_time = request.POST.get('schedule_end_time', None)
        schedule_days = request.POST.getlist('schedule_days', None)
        schedule_hours = request.POST.getlist('schedule_hours', None)

        if count:
            kwargs.update({"count": count})

        if schedule_end_date:
            assert schedule_end_time

            schedule_end_datetime = time_to_utc(date=schedule_end_date, time=schedule_end_time, timezone=timezone)
            # Count and Until cannot coexist in datetime.rrule. We will prioritize until over count.
            kwargs.update({"until": schedule_end_datetime, "count": None})

        # For the next two blocks, we want to turn a list of strings into a string. [1, 2, 3] is the goal.
        if schedule_days:
            days = []
            for day in schedule_days:
                days.append(int(day))
            kwargs.update({"byweekday": str(days)})

        if schedule_hours:
            hours = []
            offset = int(datetime.utcnow().astimezone(ZoneInfo(timezone)).strftime('%z')[:3])
            for hour in schedule_hours:
                hours.append(int(hour) - offset)
            kwargs.update({"byhour": str(hours)})

        kwargs.update({"interval": request.POST.get('schedule_interval'), "freq": request.POST.get('schedule_units')})
    else:
        # This is how we will present a one-time reminder to dateutil.rrule
        kwargs.update({"freq": "MINUTELY", "interval": 1})

    reminder_id = request.POST.get('reminder_id')

    if reminder_id:
        models.Reminder.objects.filter(pk=reminder_id, recipient=request.user.id).update(**kwargs)
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
    return redirect('home')


class HomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            filtered_data = filters.RemindersFilter(request=request, queryset=models.Reminder.objects.all())
            # Actual results of the filter is found as filtered_data.qs, not .data as that dumps the raw input
            # of the filter.
            table = tables.RemindersTable(data=filtered_data.qs, empty_text="You currently have no reminders!")
            return render(request, 'get_reminders.html', {'table': table, 'CreateButtonForm': forms.CreateButtonForm})
        return render(request, "index.html", {'auth_url': auth_url})


@login_required(login_url='oauth/discord_login')
@require_http_methods(["GET"])
def forget(request):
    models.Reminder.objects.filter(recipient=request.user.id).delete()
    models.DiscordUser.objects.filter(id=request.user.id).delete()
    logout(request)

    return render(request, "forgotten.html", {'home': reverse('home')})


class ReminderView(View):
    # Where is PUT and DELETE? crispy forms doesn't support using PUT on forms, so we can only GET and POST.
    def get(self, request):
        reminder_id = request.GET.get('id', None)
        error_message = request.GET.get('error', None)
        reminder = None
        target_template = 'create_reminder.html'
        render_kwargs = {}
        message = 'You are creating a new reminder.'

        if reminder_id:
            try:
                reminder = models.Reminder.objects.get(pk=reminder_id, recipient=request.user.id)
            except ObjectDoesNotExist:
                return HttpResponseForbidden()
            message = 'You are editing an existing reminder.'

            delete_form = forms.DeleteConfirmationForm(reminder=reminder)
            render_kwargs.update({'DeleteConfirmationForm': delete_form})
            target_template = 'edit_reminder.html'

        if error_message:
            message = error_message

        form = forms.ReminderForm(request=request, reminder=reminder)
        render_kwargs.update({'message': message, 'ReminderForm': form})
        return render(request, target_template, render_kwargs)

    @method_decorator(login_required(login_url="oath/discord_login"))
    def post(self, request):
        reminder_id = request.POST.get("reminder_id", None)
        delete = request.POST.get("delete", None)

        if delete:  # crispy-forms only supports GET and POST, so DELETE is mashed into here.
            if not reminder_id:
                return HttpResponseForbidden()

            try:
                reminder = models.Reminder.objects.get(pk=reminder_id, recipient=request.user.id)
            except ObjectDoesNotExist:
                return HttpResponseForbidden()

            if reminder:
                reminder.delete()

            return redirect("home")

        request.session['timezone'] = request.POST.get('timezone', None)

        try:
            parse_reminder(request=request)  # Handles both creating new and editing existing
            return redirect("home")
        except ValueError:
            message = 'One or more values were not understood. Please try again.'
        except AssertionError:
            message = 'One or more required values were missing. Please check your input and try again.'
        except ValidationError:
            message = "One or more dates or times were invalid. Please check your input and try again."

        if not message:
            message = 'An unhandled error occurred. Sorry.'

        return redirect("reminder", error=message, id=reminder_id)
