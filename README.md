## CinnamonSwirl WebApp
****
This allows you to see, create, edit and delete reminders for the Discord bot [CinnamonSwirl](https://github.com/CinnamonSwirly/CinnamonSwirl).

It's not meant to be standalone. This was made as a learning experience to explore the basics of Django and thus, 
may be missing a lot of features some would consider mandatory. It is provided as-is under the Creative Commons Zero v1.0 Universal license.

### Requirements
* MariaDB or MySQL instance, can be a container or standalone. Cloud instances not tested.
* A registered Discord application. Can be the same as the one you use for the Discord bot.
* If building with the attached dockerfile, only docker 20.10.12 or higher is required to build the project.
* If running without docker, the following are required:
  * Python 3.10 or greater
  * The following python libraries:
    * django 4.1.2
    * django-filter 22.1.0
    * django-crispy-forms 1.14.0
    * django-tables2 2.4.1
    * django-bootstrap3 22.1
    * django-debug-toolbar 3.7.0
    * mysqlclient 2.1.1
    * gunicorn 20.1.0
    * requests 2.25.1

### Setup
* Docker:
  1. Fork this repo and set up an access token.See: [GitHub Documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
  2. Build an image with the attached dockerfile. There are build arguments to provide:
     * URL: A ``https://token:<password>@github.com/repo`` URL you can clone the repo from. 
     * LOGGING_LEVEL: The level you want gunicorn to log. DEBUG, INFO, WARNING or ERROR. See: [Gunicorn Documentation](https://docs.gunicorn.org/en/latest/settings.html#logging)
     * BRANCH: The branch of the repo you wish to clone and run. Usually this should be set to main
  3. Create a container from the image you built.
     * Be sure you've included all the [Environment Variables]()
     * Be sure to redirect port 443 to any port you want to use on your host. Ideally 443, 9443 or similar.
  4. Enjoy! You can access the app using the IP/HOST:Port combination in your browser.
* Python Standalone:
  1. Set your environment variables. See: [Environment Variables]()
  2. Ensure you meet all requirements above.
  3. Clone the repo.
  4. Launch gunicorn using "gunicorn --bind=0.0.0.0:443 App.wsgi"
     * Extended settings and optional parameters available here: [Gunicorn Documentation](https://docs.gunicorn.org/en/latest/settings.html)
  5. Access the app via a browser at the IP/Host:Port of your server or desktop you're running this on.

### Feedback is welcome, feel free to open an issue!