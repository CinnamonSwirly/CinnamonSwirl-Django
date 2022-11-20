from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field, Fieldset
from django.urls import reverse
from datetime import datetime
from typing import Tuple, Union
from zoneinfo import ZoneInfo


class ReminderForm(forms.Form):
    """
    This form is shown when creating or editing a reminder. When creating, only basic initial values are applied.
    When editing, a models.Reminder object must be passed to it, so it can read those values and apply them to the
    form's fields. Will either POST to create_reminder or edit_reminder depending on if a Reminder is supplied.
    """
    startDate = forms.DateTimeField(required=True, label="",
                                    widget=forms.DateInput(attrs={'type': 'date', 'format': '%mm %dh %yyyy'}))
    startTime = forms.DateTimeField(required=True, initial='14:30', label="",
                                    widget=forms.DateTimeInput(attrs={'type': 'time', 'format': '%H:%M'}))
    timezone = forms.ChoiceField(required=True, choices=[])
    message = forms.CharField(required=True, initial="Your message here.",
                              widget=forms.Textarea(attrs={'type': 'text'}))
    routine = forms.BooleanField(label="Does this reminder reoccur on a schedule?", initial=False,
                                 widget=forms.CheckboxInput(), required=False)
    schedule_interval = forms.ChoiceField(required=False, label="Every..", choices=[])
    schedule_units = forms.ChoiceField(required=False, choices=[("MINUTELY", "Minutes"), ("DAILY", "Days"),
                                                                ("WEEKLY", "Weeks"), ("MONTHLY", "Months"),
                                                                ("YEARLY", "Years")], label="")
    count = forms.ChoiceField(required=False, label="Repeat X times:", choices=[])
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
        """
        :param request: Must contain a session for the logged-in user.
        :param reminder: models.Reminder
        :param args: Internal django-crispy-forms use only
        :param kwargs: Internal django-crispy-forms use only
        """
        super(ReminderForm, self).__init__(*args, **kwargs)
        self.request = request
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
            Fieldset("(Optional) Set up a routine for this reminder:",
                     Field("routine"),
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
                              Field("schedule_end_time"))
                     )

        )

        self.fields['timezone'].choices = self.timezones
        self.fields['schedule_days'].choices = self.days
        self.fields['schedule_interval'].choices = self.intervals(1, 32)
        self.fields['schedule_hours'].choices = self.intervals(0, 24)
        self.fields['count'].choices = self.intervals(1, 101)

        if reminder:
            date, time = self.change_timezone(time=reminder.dtstart,
                                              primary_timezone=self.request.session.get("timezone"),
                                              fallback_timezone=reminder.timezone)
            self.set_initial_values(message=reminder.message, startDate=date, startTime=time,
                                    timezone=self.read_timezone(reminder.timezone), recipient=reminder.recipient,
                                    reminder_id=reminder.id, recipient_friendly=self.request.user.discord_tag)

            self.helper.form_action = reverse('edit_reminder')

            if reminder.byweekday or reminder.byhour or reminder.until:
                if reminder.until:
                    _date, _time = self.change_timezone(time=reminder.until,
                                                        primary_timezone=self.request.session.get("timezone"),
                                                        fallback_timezone=reminder.timezone)
                    self.set_initial_values(schedule_end_date=_date, schedule_end_time=_time, routine=True)

                if reminder.byweekday:
                    self.set_initial_values(routine=True,
                                            schedule_days=self.read_str_as_list(reminder.byweekday))

                if reminder.byhour:
                    hours = self.read_str_as_list(reminder.byhour)
                    self.set_initial_values(routine=True,
                                            schedule_hours=self.change_hours_from_utc(
                                                hours, self.request.session.get("timezone"), reminder.timezone))

                if reminder.count is not None:
                    if reminder.count > 1:
                        self.set_initial_values(routine=True, count=reminder.count)

                self.set_initial_values(schedule_interval=reminder.interval, schedule_units=reminder.freq)
        else:
            self.set_initial_values(recipient=self.request.user.id, recipient_friendly=self.request.user.discord_tag,
                                    timezone=self.read_timezone(request.session.get('timezone')),
                                    reminder_id=request.GET.get('id'))
            self.helper.form_action = reverse('create_reminder')

        self.helper.add_input(Submit('submit', 'Submit'))

    def set_initial_values(self, **kwargs):
        """
        :param kwargs: A dict of field names as keys and desired values.
        :return: None
        """
        for kwarg in kwargs:
            self.fields[kwarg].initial = kwargs[kwarg]

    @property
    def timezones(self) -> list:
        """
        Note the first value in each tuple is what django sees. The second is what the user sees.
        :return: list of tuples
        """
        return [("US/Eastern", "USA Eastern"), ("US/Central", "USA Central"), ("US/Mountain", "USA Mountain"),
                ("US/Pacific", "USA Pacific")]

    @property
    def timezones_as_dict(self) -> dict:
        """
        Note the first value in each tuple is what django sees. The second is what the user sees.
        This is useful for receiving a value from edit_reminder and matching it to a value in the form field.
        :return: dict of tuples
        """
        return {"US/Eastern": ("US/Eastern", "USA Eastern"), "US/Central": ("US/Central", "USA Central"),
                "US/Mountain": ("US/Mountain", "USA Mountain"), "US/Pacific": ("US/Pacific", "USA Pacific")}

    @property
    def days(self):
        return [(5, "Saturday"), (4, "Friday"), (3, "Thursday"), (2, "Wednesday"), (1, "Tuesday"), (0, "Monday"),
                (6, "Sunday")]

    @staticmethod
    def intervals(start: int, stop: int) -> list:
        """
        This generates a list of tuples with range(1, 32). Each tuple is an int, str combo.
        Note the first value in each tuple is what django sees. The second is what the user sees.
        Used to populate the schedule_interval field.
        :return: list of tuples
        """
        result = []
        for i in range(start, stop):
            t = (i, i)
            result.append(t)
        return result

    def read_timezone(self, timezone: str) -> Union[tuple, None]:
        """
        Matches the timezone to the right tuple for setting the initial value of the timezone field.
        Note the timezone is usually given by edit_reminder
        :param timezone:
        :return: tuple or None
        """
        try:
            return self.timezones_as_dict[timezone]
        except KeyError:
            return None

    @staticmethod
    def read_str_as_list(string: str) -> list:
        dirty = string.replace("[", '').replace("]", '').split(',')
        clean = []
        for item in dirty:
            try:
                clean.append(int(item))
            except ValueError:
                clean.append(item)
        return clean

    @staticmethod
    def change_timezone(time: datetime, primary_timezone: Union[str, None],
                        fallback_timezone: Union[str, None] = None) -> Tuple[str, str]:
        """
        Attempts to change the supplied datetime from UTC to the supplied primary timezone. A fallback timezone can be
        provided. Leaves the timezone in UTC if both timezones are None.
        :param time: datetime, usually supplied by the request
        :param primary_timezone: Usually request.session.user.timezone. Needs to be a valid timezone from zoneinfo
        :param fallback_timezone: Usually reminder.timezone. Needs to be a valid timezone from zoneinfo
        :return: tuple of formatted strings for DateTimeFields. One for the date and one for the time.
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
        return response.strftime('%Y-%m-%d'), response.strftime('%H:%M')

    @staticmethod
    def change_hours_from_utc(hours: list, primary_timezone: str | None, fallback_timezone: str | None = None) -> list:
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
    POSTs to delete_reminder. Requires the user checkbox a confirmation before submitting.
    """
    reminder_id = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'readonly': True}))
    confirmation = forms.BooleanField(required=True, label="Check this and click delete below to delete this reminder.")

    def __init__(self, reminder=None, *args, **kwargs):
        super(DeleteConfirmationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_action = reverse('delete_reminder')
        self.fields['reminder_id'].initial = reminder.id
        self.helper.layout = Layout(
            Field('reminder_id'),
            Field('confirmation'),
            Submit('submit', 'Delete')
        )


class CreateButtonForm(forms.Form):
    """
    Sends the user to create_reminder. Usually found on list_reminders.
    """
    def __init__(self, *args, **kwargs):
        super(CreateButtonForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_action = reverse('create_reminder')
        self.helper.layout = Layout(
            Submit('submit', 'Create New Reminder')
        )
