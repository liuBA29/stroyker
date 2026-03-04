from constance import config


def ycaptcha_context(request):
    return {
        'YCAPTCHA_ENABLED': bool(
            all(
                (
                    config.CAPTCHA_MODE == 'yandex',
                    config.YCAPTCHA_CLIENT_KEY,
                    config.YCAPTCHA_SERVER_KEY,
                )
            )
            and any(
                (
                    config.RECAPTCHA_REGISTRATION_FORM,
                    config.RECAPTCHA_FEEDBACK_FORM,
                    config.RECAPTCHA_CALLME_FORM,
                    config.RECAPTCHA_CART_FORM,
                    config.RECAPTCHA_CUSTOM_FORMS,
                    config.CAPTCHA_USE_FOR_BOOKING_FORM,
                )
            )
        )
    }
