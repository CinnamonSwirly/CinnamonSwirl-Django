import doctest
import os
import sys
import django
from selenium import webdriver
from django.test import TestCase
from django.urls import reverse
from django.http import HttpRequest

sys.path.append(os.path.abspath('../..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'App.settings'

django.setup()

from CinnamonSwirl import apps, auth, filters, forms, managers, models, tables, views


def load_tests(loader, tests, ignore):
    modules = (apps, auth, filters, forms, managers, models, tables, views)
    for module in modules:
        tests.addTests(doctest.DocTestSuite(module))
    return tests


class MockUser:
    def __init__(self):
        self.id = 0


class MockSession:
    def __init__(self):
        pass


class MockPOST:
    def __init__(self):
        self.values = {'recipient': 0, 'message': "TEST", 'schedule_units': 'MINUTELY', 'schedule_interval': 1,
                       'startDate': '2022-12-01', 'startTime': '09:00', 'timezone': 'US/Central'}

    def get(self, value, default=None):
        if value in self.values.keys():
            return self.values[value]
        return default

    def getlist(self, value, default=None):
        return self.get(value, default)


class MockRequest(HttpRequest):
    def __init__(self):
        super(MockRequest).__init__()
        self.session = MockSession()
        self.POST = MockPOST()
        self.user = MockUser()


class Tests(TestCase):

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_mock_reminder(self):
        request = MockRequest()
        parsed = views.parse_reminder(request)
        self.assertTrue(parsed)

        reminder = models.Reminder.objects.get(recipient=0)
        self.assertEqual(reminder.message, 'TEST')

    def test_selenium_homepage(self):
        # IN PROGRESS
        driver = webdriver.Chrome('./chromedriver')
        driver.get("http://127.0.0.1:80")
        print(driver.title)
