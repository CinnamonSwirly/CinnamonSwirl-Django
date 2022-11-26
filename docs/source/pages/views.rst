Views
=====

HOME
----
.. autoclass:: CinnamonSwirl.views.HomeView
.. automethod:: CinnamonSwirl.views.HomeView.get

| After login HomeView will render the reminders page instead of the explanation front page.

OAUTH2
------
When authenticating, the process begins with the user visiting Discord's OAuth2 URL defined in the environment
variable, DISCORD_AUTH_URL. The user is sent back to us with an access code (aka a token) and we will use that to
get the user's information such as profile picture, discord user ID, and username.

.. autofunction:: CinnamonSwirl.views.discord_login

| Sends to: :doc:`DISCORD_AUTH_URL <environment variables>`

.. autofunction:: CinnamonSwirl.views.discord_login_redirect

.. autofunction:: CinnamonSwirl.views.exchange_code

| Creates a :doc:`DiscordUser <models>` using :doc:`DiscordAuthenticationBackend <auth>`
    and :doc:`DiscordUserOAuth2Manager <auth>`, then Sends to homepage

REMINDERS
---------
.. autoclass:: CinnamonSwirl.views.ReminderView
    :members: get, post

.. autofunction:: CinnamonSwirl.views.parse_reminder

.. autofunction:: CinnamonSwirl.views.time_to_utc

| See: :doc:`Reminder <models>`, :doc:`Forms <forms>`

ACCOUNT
-------
.. autofunction:: CinnamonSwirl.views.logout

.. autofunction:: CinnamonSwirl.views.forget


