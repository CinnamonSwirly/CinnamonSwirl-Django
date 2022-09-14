import django_filters
from CinnamonSwirl import models


class RemindersFilter(django_filters.FilterSet):
    """
    A basic filter setup from django_filters. The user must be logged in so we can get their discord user ID. We will
    use this against Reminder.recipient to see only Reminders that the user owns.
    """
    completed = django_filters.BooleanFilter()

    class Meta:
        model = models.Reminder
        fields = ['completed']

    @property
    def qs(self):
        parent = super().qs
        user = getattr(self.request, 'user', None)
        if user:
            user_id = getattr(self.request.user, 'id', None)
            if user_id:
                return parent.filter(recipient=user_id)
        return parent.filter()
