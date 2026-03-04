import functools
import weakref


class cached_classproperty:

    def __init__(self, fget):
        self.obj = {}
        self.fget = fget

    def __get__(self, owner, cls):
        if cls in self.obj:
            return self.obj[cls]
        self.obj[cls] = self.fget(cls)
        return self.obj[cls]


def ajax_required(func):
    from django.http import HttpResponseBadRequest
    from django.conf import settings
    from django.shortcuts import redirect

    def wrap(request, *args, **kwargs):
        if not request.is_ajax():
            ref = request.META.get('HTTP_REFERER')
            if ref and ref.startswith(settings.BASE_URL):
                return redirect(ref)
            return HttpResponseBadRequest()
        return func(request, *args, **kwargs)
    wrap.__doc__ = func.__doc__
    wrap.__name__ = func.__name__
    return wrap


def memoized_method(*lru_args, **lru_kwargs):
    def decorator(func):
        @functools.wraps(func)
        def wrapped_func(self, *args, **kwargs):
            # We're storing the wrapped method inside the instance. If we had
            # a strong reference to self the instance would never die.
            self_weak = weakref.ref(self)

            @functools.wraps(func)
            @functools.lru_cache(*lru_args, **lru_kwargs)
            def cached_method(*args, **kwargs):
                return func(self_weak(), *args, **kwargs)
            setattr(self, func.__name__, cached_method)
            return cached_method(*args, **kwargs)
        return wrapped_func
    return decorator
