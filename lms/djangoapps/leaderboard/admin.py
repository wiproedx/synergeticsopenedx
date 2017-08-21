from django.contrib import admin
from .models import LeaderBoard


@admin.register(LeaderBoard)
class LeaderBoardAdmin(admin.ModelAdmin):
    list_display = ['student', 'course_id', 'points', 'has_passed']
    list_filter = ['has_passed']

    class Meta:
        verbose_name = "Leaderboard"
        verbose_name_plural = "Leaderboard"
