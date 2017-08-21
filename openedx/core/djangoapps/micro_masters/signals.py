"""
Signal handler for invalidating cached course overviews
"""
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save

from .models import Courses
from xmodule.modulestore.django import SignalHandler
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview


@receiver(post_save, sender=CourseOverview)
def _listen_for_course_publish(sender, instance, **kwargs):
    Courses.create_or_update_from_course_overview(instance)


@receiver(SignalHandler.course_deleted)
def _listen_for_course_delete(sender, course_key, **kwargs):  # pylint: disable=unused-argument
    """
    Catches the signal that a course has been deleted from Studio and
    invalidates the corresponding Course cache entry if one exists.
    """
    Courses.objects.filter(course_key=course_key).delete()
