FROM python:3

RUN apt-get update && \
	apt-get install python3-pip -y && \
	apt-get install libpq-dev python3-dev -y

RUN pip install --upgrade pip && \
	pip install django==4.1.2 && \
	pip install django_tables2==2.4.1 && \
	pip install django-crispy-forms==1.14.0 && \
	pip install django-debug-toolbar==3.7.0 && \
	pip install django-filter==22.1 && \
	pip install django-bootstrap3==22.1 && \
	pip install mysqlclient==2.1.1 && \
	pip install gunicorn==20.1.0 && \
	pip install requests==2.25.1 && \
	pip install discord==2.1.0

ARG URL
ARG BRANCH
RUN git clone --branch $BRANCH $URL

WORKDIR /CinnamonSwirl-Django

RUN python3 manage.py makemigrations
RUN python3 manage.py migrate

ARG LOG_LEVEL
ENV LOG_LEVEL ${LOG_LEVEL}
CMD gunicorn --bind=0.0.0.0:443 --log-level=${LOG_LEVEL} --access-logfile=- --capture-output App.wsgi
EXPOSE 443/tcp