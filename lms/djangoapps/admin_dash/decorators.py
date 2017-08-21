from django.http import Http404


def site_administrator_only(function):
    def wrap(request, *args, **kwargs):
        if request.user.is_superuser:
            return function(request, *args, **kwargs)
        else:
            raise Http404()
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap


def site_manager(function):
    def wrap(request, *args, **kwargs):
        if request.user.profile.site_manager or request.user.is_superuser:
            return function(request, *args, **kwargs)
        else:
            raise Http404()
    wrap.__doc__ = function.__doc__
    wrap.__name__ = function.__name__
    return wrap
