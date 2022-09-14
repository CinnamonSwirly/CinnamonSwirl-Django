from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field
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
    startDate = forms.DateTimeField(required=True, label="Start Date",
                                    widget=forms.DateInput(attrs={'type': 'date', 'format': '%mm %dh %yyyy'}))
    startTime = forms.DateTimeField(required=True, initial='14:30', label="Start Time",
                                    widget=forms.DateTimeInput(attrs={'type': 'time', 'format': '%H:%M'}))
    timezone = forms.ChoiceField(required=True, choices=[])
    message = forms.CharField(required=True, initial="Your message here.", label="Message",
                              widget=forms.Textarea(attrs={'type': 'text'}))
    routine = forms.BooleanField(label="Does this reminder reoccur on a schedule?", initial=False,
                                 widget=forms.CheckboxInput(), required=False)
    schedule_date = forms.DateTimeField(required=False, label="Next Scheduled Date",
                                        widget=forms.DateInput(attrs={'type': 'date', 'format': '%mm %dh %yyyy'}))
    schedule_time = forms.DateTimeField(required=False, label="Next Scheduled Time",
                                        widget=forms.DateTimeInput(attrs={'type': 'time', 'format': '%H:%M'}))
    schedule_interval = forms.ChoiceField(required=False, label="Reoccur how often? Every..", choices=[])
    schedule_units = forms.ChoiceField(required=False, choices=[("hours", "Hours"), ("days", "Days"),
                                                                ("weeks", "Weeks"), ("months", "Months"),
                                                                ("years", "Years")], label="")
    schedule_days = forms.MultipleChoiceField(label="Reoccur on which days?", required=False,
                                              choices=[], widget=forms.CheckboxSelectMultiple())
    schedule_end = forms.DateTimeField(required=False, label="When does the schedule end? (Blank if never)",
                                       widget=forms.DateInput(attrs={'type': 'date', 'format': '%mm %dh %yyyy'}))
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

        self.fields['timezone'].choices = self.timezones
        self.fields['schedule_days'].choices = self.days
        self.fields['schedule_interval'].choices = self.intervals

        if reminder:
            date, time = self.change_timezone(time=reminder.time, primary_timezone=self.request.session.get("timezone"),
                                              fallback_timezone=reminder.timezone)
            self.set_initial_values(message=reminder.message, startDate=date, startTime=time,
                                    timezone=self.read_timezone(reminder.timezone), recipient=reminder.recipient,
                                    reminder_id=reminder.id, recipient_friendly=self.request.user.discord_tag)

            self.helper.form_action = reverse('edit_reminder')

            if reminder.routine:
                schedule_date, schedule_time = self.change_timezone(time=reminder.start_date,
                                                                    primary_timezone=self.request.session.get(
                                                                        "timezone"),
                                                                    fallback_timezone=reminder.timezone)
                self.set_initial_values(routine=True, schedule_date=schedule_date,
                                        schedule_time=schedule_time,
                                        schedule_interval=reminder.routine_amount,
                                        schedule_units=reminder.routine_unit,
                                        schedule_days=self.read_days(reminder.routine_days),
                                        schedule_end=reminder.end_date)
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
    def days(self) -> list:
        """
        Note the first value in each tuple is what django sees. The second is what the user sees.
        days is stored as a byte, hence the ints.
        :return: list of tuples
        """
        return [(64, "Saturday"), (32, "Friday"), (16, "Thursday"), (8, "Wednesday"), (4, "Tuesday"), (2, "Monday"),
                (1, "Sunday")]

    @property
    def days_as_dict(self) -> dict:
        """
        Note the first value in each tuple is what django sees. The second is what the user sees.
        This is useful for receiving a value from edit_reminder and matching it to a value in the form field.
        :return:
        """
        return {"Saturday": 64, "Friday": 32, "Thursday": 16, "Wednesday": 8, "Tuesday": 4, "Monday": 2, "Sunday": 1}

    @property
    def intervals(self) -> list:
        """
        This generates a list of tuples with range(1, 32). Each tuple is an int, str combo.
        Note the first value in each tuple is what django sees. The second is what the user sees.
        Used to populate the schedule_interval field.
        :return: list of tuples
        """
        result = []
        for i in range(1, 32):
            t = (i, str(i))
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

    def read_days(self, days: int) -> list:
        result = []
        for number, day in self.days:
            if days >= number:
                days -= number
                result.append(number)
        return result

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
