import logging
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
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import redirect, reverse, render
from django.views.decorators.http import require_http_methods
from requests import post as requests_post, get as requests_get

from CinnamonSwirl import filters, forms, models, tables, utils

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
    | |requires| code: str from Discord's OAuth2 URL for this application
    | |contains| JSON with fields matching DiscordUser

    Interacts with Discord's OAuth2 API, identifying this app, specifying permissions desired, and giving an access
    code generated from a user authorizing the application using the DISCORD_AUTH_URL environment variable.
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
    | |requires| All relevant fields for a Reminder. At least timezone, startDate, startTime, message and timezone.

    Attempts to format the request attributes from the supplied request and sends them to the Reminder
    model manager. If fed an existing reminder via a reminder_id parameter in the request, it will attempt to
    update that existing reminder instead of making a new one. This function only tries to look at POST requests.
    :raises AssertionError: If an attribute is missing
    :raises ValueError: If a date was invalid
    """
    required_fields = ["timezone", "startDate", "startTime", "message", "timezone"]
    for field in required_fields:
        assert request.POST.get(field)

    timezone = request.POST.get('timezone')

    start_datetime = time_to_utc(date=request.POST.get('startDate'), time=request.POST.get('startTime'),
                                 timezone=timezone)

    kwargs = {"dtstart": start_datetime, "timezone": timezone, "message": request.POST.get('message'),
              "recipient": request.POST.get('recipient'), "finished": False}

    class CleanedRoutineData:
        """
        The form passes blanks or None as '' instead of leaving the fields out. This is fine when evaluating booleans
        but is not acceptable by the Reminder model's manager. The values are cycled through and set to None in that
        case.
        """
        def __init__(self, _request):
            self.count = request.POST.get('count', None)
            self.schedule_end_date = request.POST.get('schedule_end_date', None)
            self.schedule_end_time = request.POST.get('schedule_end_time', None)
            self.schedule_days = request.POST.getlist('schedule_days', None)
            self.schedule_hours = request.POST.getlist('schedule_hours', None)

            fields_to_clean = ("count", "schedule_end_date", "schedule_end_time", "schedule_days", "schedule_hours")
            for _field in fields_to_clean:
                value = getattr(self, _field)
                if type(value) is str and not value:
                    setattr(self, _field, None)

    cleaned_routine_data = CleanedRoutineData(request)

    if cleaned_routine_data.schedule_end_date:
        assert cleaned_routine_data.schedule_end_time

        schedule_end_datetime = time_to_utc(date=cleaned_routine_data.schedule_end_date,
                                            time=cleaned_routine_data.schedule_end_time, timezone=timezone)
        # Count and Until cannot coexist in datetime.rrule. We will prioritize until over count.
        kwargs.update({"until": schedule_end_datetime, "count": None})

    # For the next two blocks, we want to turn a list of strings into a string. [1, 2, 3] is the goal.
    if cleaned_routine_data.schedule_days:
        days = []
        for day in cleaned_routine_data.schedule_days:
            days.append(int(day))
        kwargs.update({"byweekday": str(days)})

    if cleaned_routine_data.schedule_hours:
        hours = []
        offset = int(datetime.utcnow().astimezone(ZoneInfo(timezone)).strftime('%z')[:3])
        for hour in cleaned_routine_data.schedule_hours:
            hours.append(int(hour) - offset)
        kwargs.update({"byhour": str(hours)})

    kwargs.update({"interval": request.POST.get('schedule_interval'), "freq": request.POST.get('schedule_units'),
                   "count": cleaned_routine_data.count})

    reminder_id = request.POST.get('reminder_id')

    if reminder_id:
        try:
            models.Reminder.objects.filter(pk=reminder_id, recipient=request.user.id).update(**kwargs)
        except ObjectDoesNotExist:
            raise PermissionError
        return True
    else:
        # Do not allow users to make reminders for other people!
        if not int(request.POST.get('recipient', -1)) == int(request.user.id):
            raise PermissionError
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
def discord_login(request):
    """
    Sends the user to Discord's OAuth endpoint to do their thing.
    :param request: No requirements.
    :return: HTTPRedirect
    """
    if request:
        return redirect(auth_url)


@require_http_methods(["GET"])
def discord_login_redirect(request):
    """
    Receives the user back from discord_login. Hopefully they have been given all they need from Discord.
    Gets a token from discord with the authorization code received.
    If REGISTRATIONS_ENABLED is True, creates a new DiscordUser. If False, only allows existing users to connect.
    Leverages django's built-in authentication from here. See auth, models, and managers.
    :param request: Must contain a 'code' attribute.
    :return: HTTPRedirect
    """
    code = request.GET.get('code')
    user = exchange_code(code)
    if not settings.REGISTRATIONS_ENABLED:
        try:
            assert 'id' in user.keys()
            models.DiscordUser.objects.get(id=user['id'])
        except (ObjectDoesNotExist, AssertionError):
            return redirect('home')
    discord_user = authenticate(request, user=user)
    login(request, discord_user)
    return redirect('home')


class HomeView(View):
    def get(self, request):
        """
        The homepage shows an explanation of the app, the bot, and a few FAQs. Users can sign in and once
        authenticated, the homepage will instead show them their current reminders, allow them to edit those reminders,
        and do a few account-related tasks such as logging out or deleting all their data.
        """
        if request.user.is_authenticated:
            if not request.user.in_setup:
                filtered_data = filters.RemindersFilter(request=request, queryset=models.Reminder.objects.all())
                # Actual results of the filter is found as filtered_data.qs, not .data as that dumps the raw input
                # of the filter.
                table = tables.RemindersTable(data=filtered_data.qs, empty_text="You currently have no reminders!")
                return render(request, 'get_reminders.html', {'table': table,
                                                              'CreateButtonForm': forms.CreateButtonForm,
                                                              'LogoutButtonForm': forms.LogoutButtonForm,
                                                              'invite_link': settings.DISCORD_SERVER_INVITE_LINK})
            return redirect(reverse('setup'))
        return render(request, "index.html", {'auth_url': auth_url})


@login_required(login_url='oauth/discord_login')
@require_http_methods(["GET"])
def forget(request):
    """
    | |login|

    Should a user choose to delete their data, everything will be wiped and the user will be logged out. The user is
    presented a page confirming their data has been deleted.
    """
    models.Reminder.objects.filter(recipient=request.user.id).delete()
    models.DiscordUser.objects.filter(id=request.user.id).delete()

    return render(request, "forgotten.html", {'home': reverse('home')})


@login_required(login_url='oauth/discord_login')
@require_http_methods(["GET"])
def logout_user(request):
    """
    | |login|
    | |redirect| Home
    """
    logout(request)
    return redirect('home')


class ReminderView(View):
    # Where is PUT and DELETE? crispy forms doesn't support using PUT on forms, so we can only GET and POST.
    @method_decorator(login_required(login_url="oath/discord_login"))
    def get(self, request):
        """
        | |login|

        Renders a ReminderForm for the user to interact with.
        If supplied an id argument, it will try to fetch a reminder that the user owns by that ID. 403 if this lookup
        fails. If found, the ReminderForm will be populated with existing values from that reminder.
        """
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
        """
        | |login|
        | |requires| All relevant fields for a Reminder. At least timezone, startDate, startTime, message and timezone.

        Attempts to understand the form inputs supplied by the user and attempts to create and save a Reminder instance.
        If fed a reminder_id in the request, it will attempt to update a reminder instead.
        If fed both a reminder_id and a truthy value for delete, it will attempt to delete that reminder.
        If a user attempts to update or delete a reminder they do not own, a 403 will be returned.
        If a user feeds bad data into the reminder, or the form feeds bad data to the view, the user will be returned
        to the edit form with the original data populated and an error message.
        """
        reminder_id = request.POST.get("reminder_id", None)
        delete = request.POST.get("delete", None)
        logging.debug(f"Called with reminder_id: {reminder_id} and delete: {delete}")

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
        except PermissionError:
            return HttpResponseForbidden()

        if not message:
            message = 'An unhandled error occurred. Sorry.'

        return redirect("reminder", error=message, id=reminder_id)


class Setup(View):
    @method_decorator(login_required(login_url="oath/discord_login"))
    def get(self, request):
        if request.user.in_setup:
            if not request.user.setup_flags:  # User needs to select to join our guild
                return render(request, 'setup.html', {'SuppliedForm': forms.GuildJoinForm})
            if request.user.setup_flags == 1:  # User needs to choose how to get messages
                return render(request, 'setup.html', {'SuppliedForm': forms.MessagePreferenceForm})
            if request.user.setup_flags == 2:  # User needs to test a message
                utils.send_test_message_signal(request.user.id)
                return render(request, 'setup.html', {'SuppliedForm': forms.TestMessageForm})

        return HttpResponseBadRequest

    @method_decorator(login_required(login_url="oath/discord_login"))
    def post(self, request):
        if not request.user.setup_flags and request.POST.get('guild_join_confirmation', None):  # User joined our guild
            return self.next(request)
        if request.user.setup_flags == 1 and request.POST.get('message_preference', None):  # User chose a method
            if request.POST.get("message_preference", None):
                utils.send_channel_creation_signal(request.user.id)
                self.save_preference(request, "message_preference")
                utils.send_test_message_signal(request.user.id)
            return self.next(request)
        if request.user.setup_flags == 2 and request.POST.get('message_confirmation', None):  # User confirms test
            request.user.in_setup = False
            request.user.save()
            return redirect(reverse('home'))
        return redirect(reverse('setup'))

    def next(self, request):
        request.user.setup_flags += 1
        request.user.save()
        return self.get(request)

    @staticmethod
    def save_preference(request, attribute):
        value = request.POST.get(attribute, None)
        if value:
            setattr(request.user, attribute, value)
            request.user.save()
