import datetime
from django.db import models


class CampusAttendance(models.Model):
    ip = models.CharField(max_length=100)
    date_visited = models.DateField(default=datetime.date.today)


class ClassroomAttendance(models.Model):
    user = models.IntegerField()
    date_visited = models.DateField(default=datetime.date.today)
