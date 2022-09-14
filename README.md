## CinnamonSwirl WebApp
****
This allows you to see, create, edit and delete reminders for the Discord bot [CinnamonSwirl](https://github.com/CinnamonSwirly/CinnamonSwirl).

It's not meant to be standalone. This was made as a learning experience to explore the basics of Django and thus, 
may be missing a lot of features some would consider mandatory. It is provided as-is under the Creative Commons Zero v1.0 Universal license.

### Requirements
* Windows 10 21H2 or later
  *  This has not been tested on any other OS but is likely to work on 'typical' Linux distributions
* MariaDB or MySQL
* Python 3.10
* The following python libraries:
  * django-filter
  * django-crispy-forms
  * django-tables2
  * django-bootstrap3
  * django-debug-toolbar
* A registered Discord application. Can be the same as the one you use for the Discord bot.

### Setup
1. Be sure you've met the requirements above.
2. After cloning, inspect the example_config.cfg file in the base directory.
3. Plug in your desired values into this config file. All values are mandatory.
4. Rename the config file to config.cfg.
5. Open a terminal window and navigate to the project directory
6. Run 'python manage.py makemigrations CinnamonSwirl'
7. Run 'python manage.py migrate CinnamonSwirl'
8. Enjoy! The project can be run with 'python manage.py runserver 9000'

### Feedback is welcome, feel free to open an issue!