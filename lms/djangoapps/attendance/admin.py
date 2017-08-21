from django.contrib import admin
from .models import CampusAttendance, ClassroomAttendance


class CampusAttendanceAdmin(admin.ModelAdmin):
    list_display = ['ip', 'date_visited']


class ClassroomAttendanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'date_visited']


admin.site.register(CampusAttendance, CampusAttendanceAdmin)
admin.site.register(ClassroomAttendance, ClassroomAttendanceAdmin)
