INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.sitemaps',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_user_agents',
    'sendit.apps.base',
    'sendit.apps.main',
    'sendit.apps.watcher',
    'sendit.apps.api',
    'sendit.apps.users',
]

THIRD_PARTY_APPS = [
    'social_django',
    'crispy_forms',
    'opbeat.contrib.django',
    'djcelery',
    'rest_framework',
    'rest_framework.authtoken',
    'guardian',
    'django_gravatar',
    'lockdown',
    'taggit',
]


INSTALLED_APPS += THIRD_PARTY_APPS
