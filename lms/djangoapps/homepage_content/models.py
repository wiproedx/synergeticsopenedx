import hashlib
import time

from django.db import models
from django_extensions.db.models import TimeStampedModel

from solo.models import SingletonModel


def content_file_name(instance, filename):
    hash_ = hashlib.sha1()
    hash_.update(str(time.time()))
    name = 'homepage/content-' + hash_.hexdigest()[:20] + '_' + filename
    return name


class Testimonials(TimeStampedModel):
    """
    Model for storing Testimonials that can be displayed on homepage.
    """
    name = models.CharField(max_length=200, null=True, blank=True)
    quotes = models.TextField(null=True, blank=True)
    profile_image = models.ImageField(
        max_length=200, upload_to=content_file_name)
    is_active = models.BooleanField(default=0)

    def image_tag(self):
        return u'<img src="%s" width="50" height="50" />' % self.profile_image.url
    image_tag.short_description = 'Profile image'
    image_tag.allow_tags = True

    class Meta:
        app_label = 'homepage_content'
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()


class StatisticalCounter(SingletonModel):

    number_of_courses = models.BooleanField(default=True)
    students_registered = models.BooleanField(default=True)
    certified_users = models.BooleanField(default=False)
    number_of_paths = models.BooleanField(default=True)
    number_of_instructors = models.BooleanField(default=True)

    def __unicode__(self):
        return u"Statistical Counter"

    class Meta:
        app_label = 'homepage_content'
        verbose_name = 'Statistical Counter'
        verbose_name_plural = 'Statistical Counter'
