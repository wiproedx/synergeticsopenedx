"""Program reindex"""

import pytz
from datetime import datetime

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test

from opaque_keys.edx.keys import CourseKey
from search.search_engine_base import SearchEngine
from .models import Program


@user_passes_test(lambda u: u.is_superuser)
def index_programs_information(request):
    """
    Add all the program to the course discovery index

    """
    INDEX_NAME = "courseware_index"
    searcher = SearchEngine.get_search_engine(INDEX_NAME)
    if not searcher:
        return

    programs = Program.objects.all()
    for program in programs:
        if program.start <= datetime.now(pytz.UTC).date():
            program_info = {
                'id': program.id,
                'course': program.id,
                'content': {
                    'display_name': program.name,
                    'overview': program.overview
                },
                'image_url': program.banner_image.url,
                'start': program.start,
                'language': program.language.code,
                'subject': program.subject.name,
                'is_program': True,
            }
        # Broad exception handler to protect around and report problems with indexing
            try:
                searcher.index('course_info', [program_info])
            except:  # pylint: disable=bare-except
                log.exception(
                    "Program discovery indexing error encountered %s",
                    program_info.get('id',''),
                )
                return HttpResponse({
                    'success': False,
                    'error': 'Program discovery indexing error encountered '
                })
                raise
    return HttpResponse({'success': True})


def index_course_programs(course_id):
    """
    reindex only the program that containts course

    """
    INDEX_NAME = "courseware_index"
    searcher = SearchEngine.get_search_engine(INDEX_NAME)
    if not searcher:
        return
    course_key = CourseKey.from_string(course_id)
    programs = Program.objects.filter(courses__course_key=course_key)
    for program in programs:
        if program.start <= datetime.now(pytz.UTC).date():
            program_info = {
                'id': program.id,
                'course': program.id,
                'content': {
                    'display_name': program.name,
                    'overview': program.overview
                },
                'image_url': program.banner_image.url,
                'start': program.start,
                'language': program.language.code,
                'subject': program.subject.name,
                'is_program': True,
            }
        # Broad exception handler to protect around and report problems with indexing
            try:
                searcher.index('course_info', [program_info])
            except:  # pylint: disable=bare-except
                log.exception(
                    "Program discovery indexing error encountered %s",
                    program_info.get('id',''),
                )
                return HttpResponse({
                    'success': False,
                    'error': 'Program discovery indexing error encountered '
                })
                raise
    return HttpResponse({'success': True})
