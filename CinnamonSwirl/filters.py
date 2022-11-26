import django_filters
from CinnamonSwirl import models


class RemindersFilter(django_filters.FilterSet):
    """
    | A basic filter setup from django_filters. The user must be logged in so we can get their discord user ID. We will
        use this against Reminder.recipient to see only Reminders that the user owns.
    """
    finished = django_filters.BooleanFilter()

    class Meta:
        model = models.Reminder
        fields = ['finished']

    @property
    def qs(self):
        parent = super().qs
        return parent.filter(recipient=self.request.user.id)
