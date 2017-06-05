from kombu import Exchange, Queue
import os

# CELERY SETTINGS
REDIS_PORT = 6379  
REDIS_DB = 0  
REDIS_HOST = os.environ.get('REDIS_PORT_6379_TCP_ADDR', 'redis')

# CELERY SETTINGS
CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'
BROKER_URL = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ENABLE_UTC = True  
CELERY_TIMEZONE = "UTC"
CELERY_DEFAULT_QUEUE = 'default'
CELERY_QUEUES = (
    Queue('default', Exchange('default'), routing_key='default'),
)
CELERY_IMPORTS = ('sendit.apps.images.tasks',
                  'sendit.apps.users.tasks', )

CELERY_RESULT_BACKEND = 'redis://%s:%d/%d' %(REDIS_HOST,REDIS_PORT,REDIS_DB)

#BROKER_URL = os.environ.get('BROKER_URL',None)
if BROKER_URL == None:
    BROKER_URL = CELERY_RESULT_BACKEND
