from django.core.mail.backends.smtp import EmailBackend

from constance import config


class ConstanceEmailBackend(EmailBackend):
    """
    Custom backend for configuring mail via Constance app.
    """
    def __init__(self, host=None, port=None, username=None, password=None,
                 use_tls=None, fail_silently=False, use_ssl=None, timeout=None,
                 ssl_keyfile=None, ssl_certfile=None,
                 **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.host = config.EMAIL_HOST or self.host
        self.port = config.EMAIL_PORT or self.host
        self.username = config.EMAIL_HOST_USER or self.username
        self.password = config.EMAIL_HOST_PASSWORD or self.password
        self.use_tls = config.EMAIL_USE_TLS
        self.use_ssl = config.EMAIL_USE_SSL

        if self.use_ssl and self.use_tls:
            raise ValueError(
                "EMAIL_USE_TLS/EMAIL_USE_SSL are mutually exclusive, so only set "
                "one of those settings to True.")
