# Django Lockdown
LOCKDOWN_ENABLED=True

LOCKDOWN_URL_EXCEPTIONS = (
    r'^/api/metrics$'   # unlock /api metrics
)
