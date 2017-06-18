from sendit.settings import (
    DOMAIN_NAME,
)

def domain_processor(request):
    return {'domain': DOMAIN_NAME}
