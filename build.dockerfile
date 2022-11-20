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
	pip install django-bootstrap3

ARG URL
RUN git clone --branch master $URL

WORKDIR /CinnamonSwirl-Django

RUN python3 manage.py makemigrations
RUN python3 manage.py migrate

CMD ["python3", "manage.py", "runserver", "0.0.0.0:80"]
EXPOSE 80/tcp