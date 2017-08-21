from django.db import models
from django.contrib.auth.models import User
from model_utils.models import TimeStampedModel


class LeaderBoard(TimeStampedModel):

    student = models.ForeignKey(User)
    course_id = models.CharField(max_length=255)
    points = models.FloatField(max_length=255, null=True)
    has_passed = models.BooleanField(default=False)

    class Meta:
        app_label = "leaderboard"
        verbose_name = 'Leaderboard'
        verbose_name_plural = 'Leaderboard'

    def __unicode__(self):
        return self.student.username

    def __repr__(self):
        return self.__unicode__()
