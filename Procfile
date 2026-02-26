release: python manage.py migrate && python manage.py createcachetable
web: gunicorn despair.wsgi --log-file -
