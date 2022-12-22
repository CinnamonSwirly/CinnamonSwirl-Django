from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, Fieldset, HTML
from django.urls import reverse
from datetime import datetime
from typing import Tuple
from zoneinfo import ZoneInfo
from App import settings


class ReminderForm(forms.Form):
    """
    | |requires| request, reminder: Reminder from models

    This form is shown when creating or editing a reminder. When creating, only basic initial values are applied.
    When editing, a models.Reminder object must be passed to it, so it can read those values and apply them to the
    form's fields. Will POST to /reminder.
    """
    startDate = forms.DateTimeField(required=True, label="",
                                    widget=forms.DateInput(attrs={'type': 'date', 'format': '%mm %dh %yyyy'}))
    startTime = forms.DateTimeField(required=True, initial='14:30', label="",
                                    widget=forms.DateTimeInput(attrs={'type': 'time', 'format': '%H:%M'}))
    timezone = forms.ChoiceField(required=True, choices=[], label="Timezone (Current time)")
    message = forms.CharField(required=True, initial="Your message here.",
                              widget=forms.Textarea(attrs={'type': 'text'}))
    schedule_interval = forms.ChoiceField(required=False, label="Every..", choices=[])
    schedule_units = forms.ChoiceField(required=False, choices=[("MINUTELY", "Minutes"), ("DAILY", "Days"),
                                                                ("HOURLY", "Hourly"), ("WEEKLY", "Weeks"),
                                                                ("MONTHLY", "Months"), ("YEARLY", "Years")], label="")
    count = forms.ChoiceField(required=False, label="This many times:", choices=[])
    schedule_days = forms.MultipleChoiceField(required=False, label='',
                                              choices=[], widget=forms.CheckboxSelectMultiple())
    schedule_hours = forms.MultipleChoiceField(required=False, label='',
                                               choices=[], widget=forms.CheckboxSelectMultiple())
    schedule_end_date = forms.DateTimeField(required=False, label='',
                                            widget=forms.DateInput(attrs={'type': 'date', 'format': '%mm %dh %yyyy'}))
    schedule_end_time = forms.DateTimeField(required=False, initial='', label="",
                                            widget=forms.DateTimeInput(attrs={'type': 'time', 'format': '%H:%M'}))
    recipient_friendly = forms.CharField(required=False, label="Discord Username",
                                         widget=forms.HiddenInput(attrs={'readonly': True}))
    recipient = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'readonly': True}))
    reminder_id = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'readonly': True}))

    def __init__(self, request, reminder=None, *args, **kwargs):
        super(ReminderForm, self).__init__(*args, **kwargs)
        self.request = request
        self.reminder = reminder
        self.timezone = request.session.get('timezone')
        self.helper = FormHelper()  # Required!!! Will not render in the template without it!!!
        self.helper.form_id = 'reminder_form'
        self.helper.form_class = 'reminder_form_class'
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset("When do you want this reminder to start?",
                     Field("startDate"),
                     Field("startTime"),
                     Field("timezone")
                     ),
            Fieldset("What do you want it to say?",
                     Field("message"),
                     Field("recipient_friendly"),
                     Field("recipient"),
                     Field("reminder_id")
                     ),
            Fieldset("Set up a schedule for this reminder:",
                     Field("schedule_interval"),
                     Field("schedule_units"),
                     Field("count"),
                     Fieldset("Reoccur on specific days of the week:",
                              Field("schedule_days"),
                              ),
                     Fieldset("Reoccur on specific hours:",
                              Field("schedule_hours")
                              ),
                     Fieldset("Stop on this date:",
                              Field("schedule_end_date"),
                              Field("schedule_end_time")
                              )
                     )
        )

        self.fields['timezone'].choices = self.timezones
        self.fields['schedule_days'].choices = self.days
        self.fields['schedule_interval'].choices = self.intervals(1, 101)
        self.fields['schedule_hours'].choices = self.intervals(0, 24)
        self.fields['count'].choices = self.intervals(1, 51)
        self.fields['count'].choices.insert(0, (None, "Forever"))

        session_timezone = self.request.session.get("timezone", None)

        if reminder:
            date, time = self.change_timezone(time=reminder.dtstart,
                                              primary_timezone=session_timezone,
                                              fallback_timezone=reminder.timezone)
            self.set_initial_values(message=reminder.message, startDate=date, startTime=time,
                                    timezone=self.read_timezone(reminder.timezone), recipient=reminder.recipient,
                                    reminder_id=reminder.id, recipient_friendly=self.request.user.discord_tag)

            self.helper.form_action = reverse('reminder')

            if reminder.byweekday or reminder.byhour or reminder.until or reminder.count:
                if reminder.until:
                    _date, _time = self.change_timezone(time=reminder.until,
                                                        primary_timezone=session_timezone,
                                                        fallback_timezone=reminder.timezone)
                    self.set_initial_values(schedule_end_date=_date, schedule_end_time=_time)

                if reminder.byweekday:
                    self.set_initial_values(schedule_days=self.read_str_as_list(reminder.byweekday))

                if reminder.byhour:
                    hours = self.read_str_as_list(reminder.byhour)
                    self.set_initial_values(schedule_hours=self.change_hours_from_utc(
                                                hours, session_timezone, reminder.timezone))

                self.set_initial_values(count=getattr(reminder, 'count', None))

                self.set_initial_values(schedule_interval=reminder.interval, schedule_units=reminder.freq)
        else:
            self.set_initial_values(recipient=self.request.user.id, recipient_friendly=self.request.user.discord_tag,
                                    timezone=self.read_timezone(session_timezone),
                                    reminder_id=request.GET.get('id'))
            self.helper.form_action = reverse('reminder')

        self.helper.add_input(Submit('submit', 'Submit'))

    def set_initial_values(self, **kwargs):
        """
        | Give it a dict of field names as keys and desired values. It will set the field's initial property to
            that value.
        """
        for kwarg in kwargs:
            self.fields[kwarg].initial = kwargs[kwarg]

    @property
    def timezones(self) -> list:
        """
        | A list of tuples representing timezone options for use in the form.
            Note the first value in each tuple is what django sees. The second is what the user sees.
        """
        supported_timezones = ("US/Eastern", "US/Central", "US/Mountain", "US/Pacific")
        result = []
        for timezone in supported_timezones:
            _date, _time = self.change_timezone(time=datetime.utcnow(),
                                                primary_timezone=timezone)
            result.append((timezone, f"{timezone} ({_time})"))
        return result

    @property
    def timezones_as_dict(self) -> dict:
        """
        | A dict of timezones that will return a tuple the form can understand.
            Note the first value in each tuple is what django sees. The second is what the user sees.
            This is useful for receiving a value from reminder and matching it to a value in the form field.
        """
        return {"US/Eastern": ("US/Eastern", "USA Eastern"), "US/Central": ("US/Central", "USA Central"),
                "US/Mountain": ("US/Mountain", "USA Mountain"), "US/Pacific": ("US/Pacific", "USA Pacific")}

    @property
    def days(self):
        """
        | A list of tuples representing day options for use in the form.
            Note the first value in each tuple is what django sees. The second is what the user sees.
        """
        return [(5, "Saturday"), (4, "Friday"), (3, "Thursday"), (2, "Wednesday"), (1, "Tuesday"), (0, "Monday"),
                (6, "Sunday")]

    @staticmethod
    def intervals(start: int, stop: int) -> list:
        """
        | This generates a list of tuples with range(1, 32). Each tuple is an int, str combo.
            Note the first value in each tuple is what django sees. The second is what the user sees.
        """
        result = []
        for i in range(start, stop):
            t = (i, i)
            result.append(t)
        return result

    def read_timezone(self, timezone: str | None) -> tuple | None:
        """
        | Matches the timezone to the right tuple for setting the initial value of the timezone field.
        """
        try:
            return self.timezones_as_dict[timezone]
        except KeyError:
            return None

    @staticmethod
    def read_str_as_list(string: str) -> list:
        """
        | Cleans an incoming string of comma-separated values, usually a list stored as str in the DB, to a list of
            ints
        """
        dirty = string.replace("[", '').replace("]", '').split(',')
        clean = []
        for item in dirty:
            try:
                clean.append(int(item))
            except ValueError:
                clean.append(item)
        return clean

    @staticmethod
    def change_timezone(time: datetime, primary_timezone: str | None,
                        fallback_timezone: str | None = None) -> Tuple[str, str]:
        """
        | Attempts to change the supplied datetime from UTC to the supplied primary timezone. A fallback timezone can be
            provided. Leaves the timezone in UTC if both timezones are None.
        """
        utc = ZoneInfo("UTC")
        time_in_utc = time.replace(tzinfo=utc)

        if primary_timezone is not None:
            local = ZoneInfo(primary_timezone)

        elif fallback_timezone is not None:
            local = ZoneInfo(fallback_timezone)

        else:
            local = ZoneInfo("UTC")

        time_in_local = time_in_utc.astimezone(tz=local)
        response = time_in_local.replace(tzinfo=None)
        # Why the split? Because we have no datetime widget for both date and time, we have to split it into two.
        return response.strftime('%Y-%m-%d'), response.strftime('%H:%M')

    @staticmethod
    def change_hours_from_utc(hours: list, primary_timezone: str | None, fallback_timezone: str | None = None) -> list:
        """
        | Grabs the offset versus UTC from the supplied timezone(s) and adds that offset to an incoming value from the
            DB to properly show the user what hours they selected. The inverse, subtracting the offset, is done
            when saving in the view.
        """
        if primary_timezone is not None:
            timezone = primary_timezone
        else:
            timezone = fallback_timezone

        offset = int(datetime.utcnow().astimezone(ZoneInfo(timezone)).strftime('%z')[:3])
        result = []
        for hour in hours:
            result.append(int(hour) + offset)

        return result


class DeleteConfirmationForm(forms.Form):
    """
    | POSTs to /reminder. Requires the user checkbox a confirmation before submitting.
    | This is added to the ReminderForm's page when editing an existing reminder.
    """
    reminder_id = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'readonly': True}))
    delete = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'readonly': True}))
    confirmation = forms.BooleanField(required=True, label="Check this and click delete below to delete this reminder.")

    def __init__(self, reminder=None, *args, **kwargs):
        super(DeleteConfirmationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('reminder')
        self.fields['reminder_id'].initial = reminder.id
        self.fields['delete'].initial = True
        self.helper.layout = Layout(
            Field('reminder_id'),
            Field('delete'),
            Field('confirmation'),
            Submit('submit', 'Delete')
        )


class CreateButtonForm(forms.Form):
    """
    | Sends the user to /reminder. Usually found on list_reminders.
    """
    def __init__(self, *args, **kwargs):
        super(CreateButtonForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_action = reverse('reminder')
        self.helper.layout = Layout(
            Submit('submit', 'Create New Reminder')
        )


class LogoutButtonForm(forms.Form):
    """
    | Sends the user to /logout. Usually found on list_reminders.
    """
    def __init__(self, *args, **kwargs):
        super(LogoutButtonForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_action = reverse('logout')
        self.helper.layout = Layout(
            Submit('submit', 'Logout')
        )


class GuildJoinForm(forms.Form):
    """
    | The first step to setting up a new user is getting the bot in a common guild with the user. They can choose to
    | join the official guild or invite the bot to their own. Inviting the bot requires 'manage server' permission by
    | default through discord.
    """
    guild_join_confirmation = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'readonly': True}))

    def __init__(self, *args, **kwargs):
        super(GuildJoinForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('setup')
        self.fields["guild_join_confirmation"].initial = True
        self.helper.layout = Layout(
            HTML("<strong>First, the bot needs to see you somehow to message you.</strong>"),
            HTML(f'<p>Please <a href="{settings.DISCORD_SERVER_INVITE_LINK}">join the official server with the Bot</a>'
                 f' and <a href="https://support.discord.com/hc/en-us/articles/217916488">Enable direct messages from'
                 f' server members</a></p><br>'),
            HTML("<string>Click next when you have joined the guild and enabled direct messages.</strong><br>"),
            Field('guild_join_confirmation'),
            Submit('submit', 'Next')
        )


class MessagePreferenceForm(forms.Form):
    """
    | As part of the new user process, or if an existing user wants to reconfigure their settings, we will ask them
    | for how they'd like to receive reminders. Valid options are via DM and via Channel.
    """
    message_preference = forms.ChoiceField(
        choices=[(True, "Send reminders to a channel"), (False, "Direct message me the reminders")], required=True)

    def __init__(self, *args, **kwargs):
        super(MessagePreferenceForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('setup')
        self.helper.layout = Layout(
            Fieldset(
                "The bot can directly message you or send you messages in a private channel just for you.",
                Field('message_preference')
            ),
            Submit('submit', 'Next')
        )


class TestMessageForm(forms.Form):
    """
    | If a user's message_preference is True, they want use to message them their reminders in a channel. They use this
    | to choose their ideal channel. Usually this is shown once to pick a guild - then again to choose a channel.
    """
    message_confirmation = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'readonly': True}))

    def __init__(self, *args, **kwargs):
        super(TestMessageForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('setup')
        self.fields['message_confirmation'].initial = True
        self.helper.layout = Layout(
            HTML("<strong>Finally, let's test a message.</strong>"),
            HTML(f'<p>The bot should message you within a minute. If you do not see anything, '
                 f'<a href="{reverse("setup")}">re-send the message.</a></p>'),
            HTML('<p>Click next once you have seen the test message come through.</p>'),
            Field('message_confirmation'),
            Submit('submit', 'Next')
        )
