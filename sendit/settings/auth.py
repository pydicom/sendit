AUTHENTICATION_BACKENDS = (
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.google.GoogleOAuth2',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.github.GithubOAuth2',
    'django.contrib.auth.backends.ModelBackend', # default
    'guardian.backends.ObjectPermissionBackend',
)

# Python-social-auth

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'sendit.apps.users.views.social_user',
    'sendit.apps.users.views.redirect_if_no_refresh_token',
    'social.pipeline.user.get_username',
    'social.pipeline.social_auth.associate_by_email',  # <--- must share same email
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details',
)


# http://psa.matiasaguirre.net/docs/configuration/settings.html#urls-options
#SOCIAL_AUTH_USER_MODEL = 'django.contrib.auth.models.User'
#SOCIAL_AUTH_STORAGE = 'social.apps.django_app.me.models.DjangoStorage'
#SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/logged-in/'
#SOCIAL_AUTH_LOGIN_ERROR_URL = '/login-error/'
#SOCIAL_AUTH_LOGIN_URL = '/login-url/'
#SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/new-users-redirect-url/'
#SOCIAL_AUTH_LOGIN_REDIRECT_URL
#SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL = '/new-association-redirect-url/'
#SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/account-disconnected-redirect-url/'
#SOCIAL_AUTH_INACTIVE_USER_URL = '/inactive-user/'

# Django Lockdown
LOCKDOWN_ENABLED=True
