
For User Grade counting:
======================== 

lms/common.py
Installed_apps = ['lms.djangoapps.leaderboard.apps.LeaderboardConfig',]

 lms/urls.py
============
urlpatterns += (
    url(r'^leaderboard/$', 'leaderboard.views.show_leaderboard', name='leaderboard'),
)

1. Create leaderboard app and migrate.
2. Enable persistent grade from admin panel: /admin/grades/persistentgradesenabledflag/
3. Changes for leaderboard:
	1. Edit edx-platform/lms/djangoapps/grades/new/course_grade.py
		-- def update(self, student, course, course_structure):
				return self._compute_and_update_grade(student, course, course_structure)

	2. Edit edx-platform/lms/djangoapps/grades/signals/handlers.py
		from .signals import COURSE_GRADE_CHANGED
		-- def recalculate_course_grade(sender, course, course_structure, user, **kwargs):
			    updated_grade = CourseGradeFactory().update(user, course, course_structure)
			    COURSE_GRADE_CHANGED.send(
			        sender=None,
			        user=user,
			        course=course,
			        grade=updated_grade,
				    )
    3. Edit edx-platform/lms/djangoapps/grades/signals/signals.py
    	COURSE_GRADE_CHANGED = Signal(
		    providing_args=[
		        'user',  # User object
		        'course',  # Course object
		        'grade',  # Course Grade object
		    ]
		)




Task:
	Take org as argument
	for the courses of org:
		Total number of enrollments/courses/passed
		course display name list - number of enrollments, number of students who have passed, number of students whose progress is > 0 but not reached to passing grade