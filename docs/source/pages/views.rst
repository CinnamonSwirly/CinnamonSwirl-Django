Views
=====

/oauth/
-------
When authenticating, the process begins with the user visiting Discord's OAuth2 URL defined in the environment
variable, DISCORD_AUTH_URL. The user is sent back to us with an access code (aka a token) and we will use that to
get the user's information such as profile picture, discord user ID, and username.

.. autofunction:: CinnamonSwirl.views.exchange_code(code)

See also: :doc:`Environment Variables <environment variables>`
