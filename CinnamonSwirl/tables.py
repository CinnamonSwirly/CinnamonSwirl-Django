import django_tables2
import zoneinfo
from CinnamonSwirl import models


class RemindersTable(django_tables2.Table):
    """
    A basic table setup from django_tables2. Note the edit column is 'linkified' which gives get_absolute_url
    per Reminder object.
    """
    # CheckboxColumn looked tempting, but unfortunately the library docs clearly state that submitting the selected data
    # is not currently supported. When I tried, it would only return the last (or greatest) ID number from what you
    # selected. It would easily work for a single item selection, but the checkboxes give the impression of being able
    # to select multiple rows. It would be a UI/UX nightmare to use.
    # TODO: Re-visit for front-end, Emi the magician claims we can get around this
    edit = django_tables2.Column(accessor="pk", linkify=True, verbose_name="Edit")

    class Meta:
        model = models.Reminder
        template_name = "django_tables2/bootstrap.html"
        fields = ("edit", "message", "time", "timezone", "completed")
        orderable = True

    @staticmethod
    def render_time(record, value):
        """
        All times are stored as UTC in the database. This will convert UTC to the Reminder's timezone.
        :param record:
        :param value:
        :return:
        """
        utc = zoneinfo.ZoneInfo("UTC")
        time_in_utc = value.replace(tzinfo=utc)
        local = zoneinfo.ZoneInfo(record.timezone)
        time_in_local = time_in_utc.astimezone(local)
        return time_in_local.strftime("%m/%d/%Y %I:%M %p")

