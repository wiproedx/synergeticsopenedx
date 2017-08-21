from django.dispatch import receiver
from lms.djangoapps.grades.signals.signals import COURSE_GRADE_CHANGED

from leaderboard.models import LeaderBoard


@receiver(COURSE_GRADE_CHANGED)
def update_leaderboard(**kwargs):
    user = kwargs.get("user")
    course = kwargs.get("course")
    grade = kwargs.get("grade")
    points = grade.percent * 100
    passing_grade = course.lowest_passing_grade * 100

    leaderboard, _created = LeaderBoard.objects.get_or_create(
        student=user,
        course_id=course.id
    )
    leaderboard.points = points
    leaderboard.has_passed = True if points >= passing_grade else False
    leaderboard.save()
