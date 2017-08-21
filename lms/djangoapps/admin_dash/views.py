import json
import requests
from collections import OrderedDict
from datetime import datetime

from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.http import Http404
from django.core.exceptions import (
    NON_FIELD_ERRORS,
    ValidationError,
    ObjectDoesNotExist
)
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404

from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore import ModuleStoreEnum
from edxmako.shortcuts import render_to_response
from openedx.core.djangoapps.user_api.accounts.api import (
    check_account_exists,
    update_account_settings
)
from openedx.core.djangoapps.user_api.errors import (
    UserNotAuthorized,
    UserNotFound,
    AccountValidationError,
    AccountUpdateError
)
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

from lms.djangoapps.grades.new.course_grade import CourseGradeFactory
from student.models import CourseEnrollment
from student.views import create_account_with_params
from student_account.views import _local_server_get

from static_pages.models import StaticPage
from courseware.courses import (
    get_courses,
    sort_by_start_date,
    sort_by_announcement,
    get_course
)
from shoppingcart.models import (
    PaidCourseRegistration,
    CourseRegCodeItem,
    Coupon
)
from leaderboard.models import LeaderBoard
from admin_dash.admin_reports.traffic import get_traffic_report
from admin_dash.admin_reports.demographics import get_demographics
from cms.djangoapps.contentstore.utils import delete_course_and_groups
from .helpers import (
    get_num_students,
    get_num_courses,
    get_num_instructors,
    get_course_overview,
    get_course_price,
    user_other_settings,
    get_user_profile,
    update_price,
    get_image_url,
    validate_coupon_details,
    get_coupons,
    get_num_programs,
    get_program_coupons,
    validate_program_coupon_details,
    get_programe_price,
    program_price_update
)
from .utils import get_last_month
from .decorators import site_administrator_only, site_manager
from openedx.core.djangoapps.micro_masters.models import (
    ProgramCoupon, Program,
    ProgramEnrollment, Subject,
    Language, Instructor,
    Institution, ProgramCertificateSignatories
)
from openedx.core.djangoapps.micro_masters.forms import (
    ProgramForm, SubjectForm,
    LanguageForm, InstructorForm,
    InstitutionForm, ProgramCertificateSignatoriesForm
)

STATIC_PAGES = {'About': 'about',
                'Faq': 'faq',
                'Privacy': 'privacy',
                'Honor': 'honor',
                'Terms Of Service': 'tos',
                'Contact': 'contact',
                'Blog': 'blog'}


@login_required
@site_manager
# @site_administrator_only
def show_dashboard(request):
    """
    This view shows admin dashboard.
    """

    # Get all students, courses and instructor count
    num_students = get_num_students()
    num_instructors = get_num_instructors()
    num_courses = get_num_courses()

    # Get traffic report data
    default_start_date_str, default_end_date_str = get_last_month()
    date_list, visitors, content_viewers = get_traffic_report(
        default_start_date_str, default_end_date_str)
    context = {}
    context = {
        'num_students': num_students,
        'num_instructors': num_instructors,
        'num_courses': num_courses,
        'start_date_str': default_start_date_str,
        'end_date_str': default_end_date_str,
        'traffic_report': {
            'date_list': date_list,
            'visitors': visitors,
            'content_viewers': content_viewers
        }

    }
    return render_to_response("admin_dash/insights/traffic.html", context)


@require_POST
@ensure_csrf_cookie
@login_required
@site_manager
def update_traffic_report(request):
    """
    This view update traffic report at admin dashboard.
    """
    # Default report dates
    default_start_date_str, default_end_date_str = get_last_month()
    # Get traffic report data
    start_dt_str = request.POST.get('start_date', default_start_date_str)
    end_dt_str = request.POST.get('end_date', default_end_date_str)
    date_list, visitors, content_viewers = get_traffic_report(
        start_dt_str, end_dt_str)

    return JsonResponse({
        'date_list': date_list,
        'visitors': visitors,
        'content_viewers': content_viewers
    })


@login_required
# @site_administrator_only
@site_manager
def demographics(request):
    """
    This view update demographic report at admin dashboard.
    """
    gender_list = []
    age, education, gender_dict, education_labels = get_demographics()
    for gender in gender_dict:
        temp_dict = {}
        temp_dict['name'] = gender
        temp_dict['y'] = gender_dict[gender]
        gender_list.append(temp_dict)
    context = {
        'age': age,
        'education': education,
        'education_labels': education_labels,
        'gender': gender_list
    }
    return render_to_response("admin_dash/insights/demographics.html", context)


@login_required
# @site_administrator_only
@site_manager
def courses_chart(request):
    """
    This view update coures enrollment report at admin dashboard.
    """
    users = User.objects.all()
    no_of_passed_users = []
    no_of_enrollments = []
    courses = []
    course_list = get_courses(request.user)
    for course in course_list:
        passed_users = 0
        passing_grade = course.lowest_passing_grade
        course = get_course(course.id, depth=None)
        enrollments = CourseEnrollment.objects.filter(course_id=course.id)
        no_of_enrollments.append(len(enrollments))
        for user in users:
            try:
                leaderboard = LeaderBoard.objects.get(
                    student=user, course_id=course.id)
                user_grade = (leaderboard.points) / 100
            except:
                user_grade = 0.0
            if user_grade >= float(passing_grade):
                passed_users += 1
        no_of_passed_users.append(passed_users)
        courses.append(str(course.display_name))
    context = {
        'no_of_enrollments': no_of_enrollments,
        'no_of_passed_users': no_of_passed_users,
        'courses': courses
    }
    return render_to_response('admin_dash/insights/courses_chart.html', context)


@login_required
# @site_administrator_only
@site_manager
def revenue_report(request):
    """
    This view update revenue report at admin dashboard.
    """
    month_wise_report = OrderedDict([
        ('1', 0),
        ('2', 0),
        ('3', 0),
        ('4', 0),
        ('5', 0),
        ('6', 0),
        ('7', 0),
        ('8', 0),
        ('9', 0),
        ('10', 0),
        ('11', 0),
        ('12', 0)
    ])
    revenue_dict = OrderedDict()
    course_list = []
    single_paid_courses = PaidCourseRegistration.objects.filter(
        status='purchased')
    multiple_paid_courses = CourseRegCodeItem.objects.filter(
        status='purchased')
    for course in single_paid_courses:
        course_price = float(course.unit_cost)
        month_wise_report[str(course.fulfilled_time.month)] += course_price
        if course.course_id in revenue_dict:
            revenue_dict[course.course_id] += course_price
        else:
            revenue_dict[course.course_id] = course_price

    for course in multiple_paid_courses:
        course_price = float(course.qty * course.unit_cost)
        month_wise_report[str(course.fulfilled_time.month)] += course_price
        if course.course_id in revenue_dict:
            revenue_dict[course.course_id] += course_price
        else:
            revenue_dict[course.course_id] = course_price

    revenue_list = revenue_dict.values()
    for course in revenue_dict.keys():
        course_overview = get_course_overview(course)
        course_name = str(
            course_overview.display_name) if course_overview is not None else str(course)
        course_list.append(course_name)

    context = {
        'month_wise_report': month_wise_report,
        'course_list': course_list,
        'revenue_list': revenue_list
    }
    return render_to_response("admin_dash/insights/revenue_report.html", context)


@login_required
@site_administrator_only
def student_details(request, **kwargs):
    """
    Fetches all the user registered on Site.
    """
    DETAILS_TO_DISPLAY = ['Username', 'Name', 'Email', 'Date Joined', 'Last Login', 'Admin',
                          'Instructor', 'Active', 'Delete?']
    NO_SORT_COLUMNS = ['Admin', 'Instructor', 'Active', 'Delete?']
    REGISTRATION_FIELD_URL = '/user_api/v1/account/registration/'
    COMMON_FIELD_TYPE = ['email', 'text', 'password', 'checkbox']
    REQUIRED_FIELD_LABEL = [unicode('Email'), unicode('Full name'), unicode('Public username'),
                            unicode('Password'), unicode('State')]
    context = {}
    users_id = {}
    students = OrderedDict()
    users = User.objects.all()
    for user in users:
        details = OrderedDict()
        details['name'] = user.profile.name
        details['email'] = user.email
        details['date_joined'] = user.date_joined.strftime("%d/%m/%Y")
        details['last_login'] = user.last_login.strftime(
            "%d/%m/%Y") if user.last_login is not None else 'No Data'
        details['is_superuser'] = user.is_superuser
        details['is_staff'] = user.is_staff
        details['is_active'] = user.is_active
        students[user.username] = details
        users_id[user.username] = user.id
    context['students'] = students
    context['users_id'] = users_id
    context['details_to_display'] = DETAILS_TO_DISPLAY
    context['common_field_type'] = COMMON_FIELD_TYPE
    context['required_fields'] = REQUIRED_FIELD_LABEL
    context['no_sort_columns'] = NO_SORT_COLUMNS
    context['resitration_fields'] = json.loads(_local_server_get(
        REGISTRATION_FIELD_URL, request.session))['fields']
    return render_to_response('admin_dash/management/student.html', context)


@login_required
@site_administrator_only
def update_user(request, user=None):
    """
    Updates user details.
    """
    REGISTRATION_FIELD_URL = '/user_api/v1/account/registration/'
    SELECT_FIELDS = ['gender', 'year_of_birth', 'level_of_education']
    MANUAL_UPDTE_FIELDS = ['checkbox']
    if request.method == "GET":
        context = {}
        user = User.objects.get(id=user)
        context = {
            'username': user.username,
            'name': user.profile.name,
            'email': user.email,
            'year_of_birth': str(user.profile.year_of_birth),
            'level_of_education': user.profile.get_level_of_education_display(),
            'gender': user.profile.get_gender_display(),
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'user_id': user.id,
            'site_manager': user.profile.site_manager
        }
        resitration_fields = json.loads(_local_server_get(
            REGISTRATION_FIELD_URL, request.session))['fields']
        for field in resitration_fields:
            option_list = []
            if field['name'] in SELECT_FIELDS:
                for option in field['options']:
                    option_list.append(option)
                context[field['name'] + unicode('_options')] = option_list
        return render_to_response('admin_dash/management/student-update.html', context)
    else:
        field_type = request.POST.get('type', '')
        field_value = request.POST.get('value', '')
        field_name = request.POST.get('name', '')
        user_id = request.POST.get('user_id', '')
        user = User.objects.get(id=user_id)
        username = user.username
        user_profile = get_user_profile(user)
        if field_type not in MANUAL_UPDTE_FIELDS:
            data_dict_update = {field_name: field_value}
            try:
                with transaction.atomic():
                    update_account_settings(
                        user, data_dict_update, username=username)
                    return JsonResponse(status=200, data={
                        'success': True,
                        'message': 'User details has been updated.'
                    })
            except UserNotAuthorized:
                return JsonResponse(status=403 if user.is_staff else 404, data={
                    'success': False,
                    'message': 'User not authorized.'
                })
            except UserNotFound:
                return JsonResponse(status=404, data={
                    'success': False,
                    'message': 'User not found.'
                })
            except AccountValidationError as err:
                return JsonResponse(status=400, data={
                    'success': False,
                    'message': 'Invalid account.'
                })
            except AccountUpdateError as err:
                return JsonResponse(status=400, data={
                    'success': False,
                    'message': err.user_message
                })
        else:
            change_to = True if field_value == 'true' else False
            try:
                with transaction.atomic():
                    if field_name != 'site_manager':
                        setattr(user, field_name, change_to)
                        user.save()
                    else:
                        setattr(user_profile, field_name, change_to)
                        user_profile.save()
                    return JsonResponse(status=200, data={
                        'success': True,
                        'message': 'User details has been updated.'
                    })
            except Exception as error:
                return JsonResponse(status=400, data={
                    'success': False,
                    'message': error.mesage
                })


@login_required
@site_administrator_only
@require_POST
def create_user(request):
    """
    Creates new user.
    """
    details = request.POST.dict()
    email = request.POST.get('email', '')
    username = details.get('username')
    save_change_button_id = request.POST.get('save-change-id', '')
    conflicts = check_account_exists(email=email, username=username)
    if conflicts:
        error = "User Already Exists"
        return JsonResponse(status=409, data={
            'errorMsg': error,
            'divId': 'student_details .create-user-error',
            'saveChangeId': save_change_button_id
        })
    details["honor_code"] = "true"
    details["terms_of_service"] = details["honor_code"]
    # To keep current user logged In.
    details["creating_user_from_site_admin"] = True
    try:
        user = create_account_with_params(request, details)
    except ValidationError as err:
        # Should only get non-field errors from this function
        assert NON_FIELD_ERRORS not in err.message_dict
        # Only return first error for each field
        errors = {
            field: [{"user_message": error} for error in error_list]
            for field, error_list in err.message_dict.items()
        }
        error = ""
        for e in errors:
            error = error + "\n" + e + ": " + errors[e][0]['user_message']
        return JsonResponse(status=400, data={
            'errorMsg': error,
            'divId': 'student_details .create-user-error',
            'saveChangeId': save_change_button_id
        })
    settings_status = user_other_settings(user.id, details)
    if settings_status.get('success', False):
        return JsonResponse(status=200, data={})
    else:
        error = settings_status.get('error_msg', '')
        return JsonResponse(status=400, data={
            'errorMsg': error,
            'divId': 'student_details .create-user-error',
            'saveChangeId': save_change_button_id
        })


@login_required
@site_administrator_only
@require_POST
def delete_user(request):
    """
    Does not actually delete user but mark the user as 'inactive'.
    """
    user_id = request.POST.get('user_id', '')
    save_change_button_id = request.POST.get('save-change-id', '')
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        return JsonResponse(status=200, data={})
    except Exception as error:
        return JsonResponse(status=400, data={
            'errorMsg': 'Invalid User',
            'divId': 'student_details .delete-user-error',
            'saveChangeId': save_change_button_id
        })


@login_required
@site_administrator_only
def view_courses(request):
    """
    Display all the courses that are available to current Microsite.
    """
    COURSE_DISPLAY_HEADER = ['Course', 'Course Number', 'Course Run', 'Total Enrollments',
                             'Active Enrollments', 'Certified', 'Price', 'Delete?']
    NO_SORT_COLUMNS = ['Certified', 'Delete?']
    context = {}
    courses_list = []
    course_details = []
    courses_list = get_courses(request.user)
    if configuration_helpers.get_value("ENABLE_COURSE_SORTING_BY_START_DATE",
                                       settings.FEATURES["ENABLE_COURSE_SORTING_BY_START_DATE"]):
        courses_list = sort_by_start_date(courses_list)
    else:
        courses_list = sort_by_announcement(courses_list)
    for course in courses_list:
        details = OrderedDict()
        details['course_name'] = course.display_name
        details['course_number'] = course.number
        details['course_run'] = course.id.run
        total_enrollments = CourseEnrollment.objects.filter(
            course_id=course.id)
        details['total_enrollments'] = len(total_enrollments)
        active_enrollments = CourseEnrollment.objects.filter(
            course_id=course.id, is_active=True)
        details['active_enrollments'] = len(active_enrollments)
        details['certificate'] = course.cert_html_view_enabled
        details['price'] = get_course_price(course)
        details['course_id'] = course.id
        course_details.append(details)
    context['course_details'] = course_details
    context['course_headers'] = COURSE_DISPLAY_HEADER
    context['no_sort_columns'] = NO_SORT_COLUMNS
    return render_to_response('admin_dash/management/courses.html', context)


@login_required
@site_administrator_only
def update_course_price(request):
    """
    Update Course Price
    """
    course_id = request.POST.get('pk', '')
    course_price = request.POST.get('value', '')
    if course_price.isdigit():
        course_price = int(course_price)
        status = update_price(course_id, course_price)
        if status.get('success', False):
            return JsonResponse(status=200, data={'course_key': course_id})
        else:
            return JsonResponse('Invalid key', status=403, safe=False)
    else:
        return JsonResponse('Invalid price', status=403, safe=False)


@login_required
@site_administrator_only
def delete_course(request):
    """
    Deletes the selected courses.
    """
    course_id = request.POST.get('course_id', '')
    save_change_button_id = request.POST.get('save-change-id')
    payload = {"term": {"course": course_id}}
    headers = {'content-type': 'application/json'}
    search_delete_1 = "http://localhost:9200/courseware_index/course_info/_query"
    search_delete_2 = "http://localhost:9200/courseware_index/courseware_content/_query"
    try:
        course_key = CourseKey.from_string(course_id)
        delete_course_and_groups(
            course_key, ModuleStoreEnum.UserID.mgmt_command)
        # Deleting from Elastic search
        requests.delete(search_delete_1, data=json.dumps(
            payload), headers=headers)
        requests.delete(search_delete_2, data=json.dumps(
            payload), headers=headers)
        return JsonResponse(status=200, data={})
    except Exception as error:
        return JsonResponse(status=400, data={
            'errorMsg': error.message,
            'divId': 'course_list .delete-course-error',
            'saveChangeId': save_change_button_id
        })


@login_required
@site_administrator_only
def view_coupons(request):
    """
    Display all the coupons that are available for Courses.
    """
    COUPON_LABELS = ['Code', 'Course Name', 'Description', 'Discount(%)', 'Created By', 'Created Date',
                     'Expiration Date', 'Active', 'Delete?']
    NO_SORT_COLUMNS = ['Description', 'Active', 'Delete?']
    coupon_details = []
    coupon_active_image_url = get_image_url('active')
    course_inactive_image_url = get_image_url('inactive')
    course_list = get_courses(request.user)
    coupons = get_coupons()
    for coupon in coupons:
        temp_dict = OrderedDict()
        temp_dict['code'] = coupon.code
        course_overview = get_course_overview(coupon.course_id)
        temp_dict['course_name'] = course_overview.display_name
        temp_dict['description'] = coupon.description
        temp_dict['percentage_discount'] = coupon.percentage_discount
        temp_dict['created_by'] = coupon.created_by.username
        temp_dict['created_date'] = coupon.created_at.date(
        ).strftime("%d/%m/%Y")
        temp_dict['expiration_date'] = coupon.expiration_date.date().strftime("%d/%m/%Y") if \
            coupon.expiration_date is not None else ''
        temp_dict[
            'status'] = coupon_active_image_url if coupon.is_active is True else course_inactive_image_url
        temp_dict['coupon_id'] = coupon.id
        coupon_details.append(temp_dict)
    context = {
        'coupon_details': coupon_details,
        'labels': COUPON_LABELS,
        'courses': course_list,
        'no_sort_columns': NO_SORT_COLUMNS
    }
    return render_to_response("admin_dash/offers/coupons.html", context)


@login_required
@require_POST
@site_administrator_only
def new_coupon(request):
    """
    Add new coupon for Course.
    """
    coupon_data = request.POST.dict()
    save_change_button_id = request.POST.get('save-change-id', '')
    valid_details = validate_coupon_details(coupon_data)
    if valid_details.get('valid', False):
        code = coupon_data.get('code')
        discount = int(coupon_data.get('discount', 0))
        course_key = valid_details.get('course_key', '')
        course_overview = get_course_overview(course_key)
        description = coupon_data.get('description', '')
        created_by = request.user
        created_at = datetime.now()
        expiration_date = coupon_data.get('expiration_date', '')
        if expiration_date != '':
            expiration_object = datetime.strptime(
                expiration_date, '%m/%d/%Y %I:%M %p')
        active = True if coupon_data.get(
            'active') == unicode('true') else False
        try:
            coupon = Coupon(code=code,
                            description=description,
                            course_id=course_key,
                            percentage_discount=discount,
                            created_by=created_by,
                            created_at=created_at,
                            is_active=active,
                            expiration_date=expiration_object,
                            course_overview=course_overview)
            coupon.save()
            return JsonResponse(status=200, data={})
        except Exception as error:
            return JsonResponse(status=400, data={
                'errorMsg': 'Sorry some error occured',
                'divId': 'coupon_list .create-coupon-error',
                'saveChangeId': save_change_button_id
            })
    return JsonResponse(status=400, data={
        'errorMsg': 'Invalid Details',
        'divId': 'coupon_list .create-coupon-error',
        'saveChangeId': save_change_button_id
    })


@login_required
@site_administrator_only
def update_coupon(request, coupon_id=None):
    """
    Update Coupon.
    """
    if request.method == 'GET':
        context = {}
        coupon = Coupon.objects.get(id=coupon_id)
        context['code'] = coupon.code
        context['course_id'] = str(coupon.course_id)
        context['description'] = coupon.description
        context['discount'] = coupon.percentage_discount
        context['expiration_data'] = coupon.expiration_date.strftime("%m/%d/%Y %I:%M:%p") if \
            coupon.expiration_date is not None else ''
        context['active'] = coupon.is_active
        context['coupon_id'] = coupon.id
        context['courses'] = get_courses(request.user)
        return render_to_response('admin_dash/offers/coupon-update.html', context)
    else:
        coupon_data = request.POST.dict()
        coupon_id = coupon_data.get("coupon_id", '')
        save_change_button_id = request.POST.get('save-change-id', '')
        valid_details = validate_coupon_details(coupon_data)
        if valid_details.get('valid', False):
            try:
                coupon = Coupon.objects.get(id=coupon_id)
                coupon.code = coupon_data.get('code', '')
                coupon.description = coupon_data.get('description', '')
                coupon.course_id = valid_details.get('course_key', '')
                coupon.percentage_discount = int(
                    coupon_data.get('discount', 0))
                coupon.created_by = request.user
                expiration_date = coupon_data.get(
                    'expiration_date', 'undefined')
                if expiration_date != 'undefined':
                    expiration_object = datetime.strptime(
                        expiration_date, '%m/%d/%Y %I:%M %p')
                    coupon.expiration_date = expiration_object
                coupon.is_active = True if coupon_data.get(
                    'active') == unicode('true') else False
                coupon.course_overview = get_course_overview(
                    valid_details.get('course_key', ''))
                coupon.save()
                return JsonResponse(status=200, data={})
            except ObjectDoesNotExist:
                return JsonResponse(status=400, data={
                    'errorMsg': 'Invalid Coupon',
                    'divId': 'coupon-update',
                    'saveChangeId': save_change_button_id
                })
            except Exception as error:
                return JsonResponse(status=400, data={
                    'errorMsg': 'Sorry some error occured',
                    "divId": 'coupon-update',
                    "saveChangeId": save_change_button_id
                })
        return JsonResponse(status=400, data={
            'errorMsg': 'Invalid Details',
            "divId": 'coupon-update',
            "saveChangeId": save_change_button_id
        })

@login_required
@site_administrator_only
@require_POST
def delete_coupon(request):
    """
    Delete Coupon.
    """
    coupon_id = request.POST.get('coupon_id', '')
    save_change_button_id = request.POST.get('save-change-id', '')
    try:
        coupon = Coupon.objects.get(id=coupon_id)
        coupon.delete()
        return JsonResponse(status=200, data={})
    except Exception as error:
        return JsonResponse(status=400, data={
            'errorMsg': 'Invalid coupon id',
            'divId': 'coupon_list .delete-coupon-error',
            'saveChangeId': save_change_button_id
        })

@login_required
@site_administrator_only
def program_coupons(request):
    """
    Display all the coupons that are available for Courses.
    """
    COUPON_LABELS = ['Code', 'Program Name', 'Description', 'Discount(%)', 'Created Date',
                     'Expiration Date', 'Active', 'Delete?']
    NO_SORT_COLUMNS = ['Description', 'Active', 'Delete?']
    coupon_details = []
    coupon_active_image_url = get_image_url('active')
    coupon_inactive_image_url = get_image_url('inactive')
    program_list = get_num_programs()
    coupons = get_program_coupons()
    for coupon in coupons:
        temp_dict = OrderedDict()
        temp_dict['code'] = coupon.code
        temp_dict['course_name'] = coupon.program.name
        temp_dict['description'] = coupon.description
        temp_dict['percentage_discount'] = coupon.percentage_discount
        temp_dict['created_date'] = coupon.created.date().strftime("%d/%m/%Y")
        temp_dict['expiration_date'] = coupon.expiration_date.date().strftime("%d/%m/%Y") if \
            coupon.expiration_date is not None else ''
        temp_dict['status'] = coupon_active_image_url if coupon.is_active is True else coupon_inactive_image_url
        temp_dict['coupon_id'] = coupon.id
        coupon_details.append(temp_dict)

    context = {
        'coupon_details': coupon_details,
        'labels': COUPON_LABELS,
        'programs': program_list,
        'no_sort_columns': NO_SORT_COLUMNS
    }
    return render_to_response("admin_dash/offers/program-coupons.html", context)




@login_required
@require_POST
@site_administrator_only
def new_program_coupon(request):
    """
    Add new coupon for Course.
    """
    coupon_data = request.POST.dict()
    save_change_button_id = request.POST.get('save-change-id', '')
    valid_details = validate_program_coupon_details(coupon_data)
    if valid_details.get('valid', False):
        code = coupon_data.get('code')
        discount = int(coupon_data.get('discount', 0))
        program = valid_details.get('program_id', '')
        description = coupon_data.get('description', '')
        expiration_date = coupon_data.get('expiration_date', '')
        if expiration_date != '':
            expiration_object = datetime.strptime(expiration_date, '%m/%d/%Y %I:%M %p')
        active = True if coupon_data.get('active') == unicode('true') else False
        try:
            coupon = ProgramCoupon(code=code,
                                   description=description,
                                   program=program,
                                   percentage_discount=discount,
                                   is_active=active,
                                   expiration_date=expiration_object)
            coupon.save()
            return JsonResponse(status=200, data={})
        except Exception as error:
            return JsonResponse(status=400, data={
                'errorMsg': 'Sorry some error occured',
                'divId': 'coupon_list .create-coupon-error',
                'saveChangeId': save_change_button_id
            })
    return JsonResponse(status=400, data={
        'errorMsg': 'Invalid Details',
        'divId': 'coupon_list .create-coupon-error',
        'saveChangeId': save_change_button_id
    })


@login_required
@site_administrator_only
def update_program_coupon(request, coupon_id=None):
    """
    Update Coupon.
    """
    if request.method == 'GET':
        context = {}
        coupon = ProgramCoupon.objects.get(id=coupon_id)
        context['code'] = coupon.code
        context['program_id'] = coupon.program.id
        context['description'] = coupon.description
        context['discount'] = coupon.percentage_discount
        context['expiration_data'] = coupon.expiration_date.strftime("%m/%d/%Y %I:%M:%p") if \
            coupon.expiration_date is not None else ''
        context['active'] = coupon.is_active
        context['coupon_id'] = coupon.id
        context['programs'] = get_num_programs()
        return render_to_response('admin_dash/offers/update-program-coupon.html', context)
    else:
        coupon_data = request.POST.dict()
        coupon_id = coupon_data.get("coupon_id", '')
        save_change_button_id = request.POST.get('save-change-id', '')
        valid_details = validate_program_coupon_details(coupon_data)
        if valid_details.get('valid', False):
            try:
                coupon = ProgramCoupon.objects.get(id=coupon_id)
                coupon.code = coupon_data.get('code', '')
                coupon.description = coupon_data.get('description', '')
                coupon.program = valid_details.get('program_id', '')
                coupon.percentage_discount = int(coupon_data.get('discount', 0))
                expiration_date = coupon_data.get('expiration_date', 'undefined')
                if expiration_date != 'undefined':
                    expiration_object = datetime.strptime(expiration_date, '%m/%d/%Y %I:%M %p')
                    coupon.expiration_date = expiration_object
                coupon.is_active = True if coupon_data.get('active') == unicode('true') else False
                coupon.save()
                return JsonResponse(status=200, data={})
            except ObjectDoesNotExist:
                return JsonResponse(status=400, data={
                    'errorMsg': 'Invalid Coupon',
                    'divId': 'coupon-update',
                    'saveChangeId': save_change_button_id
                })
            except Exception as error:
                return JsonResponse(status=400, data={
                    'errorMsg': 'Sorry some error occured',
                    "divId": 'coupon-update',
                    "saveChangeId": save_change_button_id
                })
        return JsonResponse(status=400, data={
            'errorMsg': 'Invalid Details',
            "divId": 'coupon-update',
            "saveChangeId": save_change_button_id
        })


@login_required
@site_administrator_only
@require_POST
def delete_program_coupon(request):
    """
    Delete Coupon.
    """
    coupon_id = request.POST.get('coupon_id', '')
    save_change_button_id = request.POST.get('save-change-id', '')
    try:
        coupon = ProgramCoupon.objects.get(id=coupon_id)
        coupon.delete()
        return JsonResponse(status=200, data={})
    except Exception as error:
        return JsonResponse(status=400, data={
            'errorMsg': 'Invalid coupon id',
            'divId': 'coupon_list .delete-coupon-error',
            'saveChangeId': save_change_button_id
        })


@login_required
@site_administrator_only
def site_content(request):
    """
    Displays static page content.
    """
    context = {}
    static_page = StaticPage.get_content()
    context['static_content'] = static_page
    context['static_pages'] = STATIC_PAGES
    return render_to_response("admin_dash/configuration/site_content.html", context)


@login_required
@site_administrator_only
@require_POST
def add_static_content(request):
    """
    Adds selected static page content.
    """
    page = request.POST.get('page', '')
    content = request.POST.get('content', '')
    save_change_button_id = request.POST.get('save-change-id')
    status = StaticPage.update_content(page, content)
    if status.get('success', False) is True:
        return JsonResponse(status=200, data={})
    else:
        error = status.get('error_msg', 'Sorry Some Error Occurred')
        return JsonResponse(status=400, data={
            'errorMsg': error,
            'divId': 'site_content',
            'saveChangeId': save_change_button_id
        })


@login_required
@site_administrator_only
def show_programs(request):
    """
    Display all the programs.
    """
    PROGRAM_DISPLAY_HEADER = ['Program', 'Average Length', 'Effort', 'Total Enrollments',
                             'Start Date', 'End Date', 'Price', 'Delete?']
    NO_SORT_COLUMNS = ['Delete?']
    context = {}
    program_details = []
    programs_list = get_num_programs()
    for program in programs_list:
        details = OrderedDict()
        details['program_name'] = program.name
        details['program_average_length'] = program.average_length
        details['program_effort'] = program.effort
        total_enrollments = ProgramEnrollment.objects.filter(program=program, is_active=True)
        details['total_enrollments'] = len(total_enrollments)
        details['program_start'] = program.start.strftime("%d/%m/%Y") if program.start is not None else ''
        details['program_end'] = program.end.strftime("%d/%m/%Y") if program.end is not None else ''
        details['price'] = get_programe_price(program)
        details['program_id'] = program.id
        program_details.append(details)
    context['program_details'] = program_details
    context['program_headers'] = PROGRAM_DISPLAY_HEADER
    context['no_sort_columns'] = NO_SORT_COLUMNS
    return render_to_response('admin_dash/management/programs_form.html', context)


@login_required
@site_administrator_only
def create_program(request, template_name='admin_dash/management/programs_create_form.html'):
    form = ProgramForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        program = form.save(commit=False)
        program.save()
        return redirect(reverse('show-programs'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def update_program(request, pk, template_name='admin_dash/management/programs_create_form.html'):
    program = get_object_or_404(Program, pk=pk)
    form = ProgramForm(request.POST or None, instance=program)
    if form.is_valid():
        form.save()
        return redirect(reverse('show-programs'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def program_delete(request, pk):
    program = get_object_or_404(Program, pk=pk)
    program.delete()
    return redirect(reverse('show-programs'))


@login_required
@site_administrator_only
def show_subject(request):
    """
    Display all the subjects.
    """
    SUBJECT_DISPLAY_HEADER = ['Subject', 'Mark As Popular', 'Delete?']
    NO_SORT_COLUMNS = ['Delete?']
    subjects = Subject.objects.all()
    context = {}
    subject_details = []
    for subject in subjects:
        details = OrderedDict()
        details['subject_name'] = subject.name
        details['mark_as_popular'] = subject.mark_as_popular
        details['subject_id'] = subject.id
        subject_details.append(details)
    context['subject_details'] = subject_details
    context['subject_headers'] = SUBJECT_DISPLAY_HEADER
    context['no_sort_columns'] = NO_SORT_COLUMNS
    return render_to_response('admin_dash/management/subject_form.html', context)


@login_required
@site_administrator_only
def add_subject(request, template_name='admin_dash/management/subject_create_form.html'):
    form = SubjectForm(request.POST or None)
    if form.is_valid():
        subject = form.save(commit=False)
        subject.save()
        return redirect(reverse('show-subjects'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def update_subject(request, pk, template_name='admin_dash/management/subject_create_form.html'):
    subject = get_object_or_404(Subject, pk=pk)
    form = SubjectForm(request.POST or None, instance=subject)
    if form.is_valid():
        form.save()
        return redirect(reverse('show-subjects'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def delete_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    subject.delete()
    return redirect(reverse('show-subjects'))


@login_required
@site_administrator_only
def show_language(request):
    """
    Display all the language.
    """
    LANGUAGE_DISPLAY_HEADER = ['Name', 'Code', 'Delete?']
    NO_SORT_COLUMNS = ['Delete?']
    languages = Language.objects.all()
    context = {}
    language_details = []
    for language in languages:
        details = OrderedDict()
        details['language_name'] = language.name
        details['code'] = language.code
        details['language_id'] = language.id
        language_details.append(details)
    context['language_details'] = language_details
    context['language_headers'] = LANGUAGE_DISPLAY_HEADER
    context['no_sort_columns'] = NO_SORT_COLUMNS
    return render_to_response('admin_dash/management/language_form.html', context)


@login_required
@site_administrator_only
def add_language(request, template_name='admin_dash/management/language_create_form.html'):
    form = LanguageForm(request.POST or None)
    if form.is_valid():
        language = form.save(commit=False)
        language.save()
        return redirect(reverse('show-language'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def update_language(request, pk, template_name='admin_dash/management/language_create_form.html'):
    language = get_object_or_404(Language, pk=pk)
    form = LanguageForm(request.POST or None, instance=language)
    if form.is_valid():
        form.save()
        return redirect(reverse('show-language'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def delete_language(request, pk):
    language = get_object_or_404(Language, pk=pk)
    language.delete()
    return redirect(reverse('show-language'))


@login_required
@site_administrator_only
def show_instructor(request):
    """
    Display all the instructor.
    """
    INSTRUCTOR_DISPLAY_HEADER = ['Name', 'Designation', 'Institution', 'Profile', 'Delete?']
    NO_SORT_COLUMNS = ['Delete?', 'Profile']
    instructors = Instructor.objects.all()
    context = {}
    instructor_details = []
    for instructor in instructors:
        details = OrderedDict()
        details['instructor_name'] = instructor.name
        details['instructor_designation'] = instructor.designation
        details['instructor_institution'] = instructor.institution
        details['instructor_profile_image'] = instructor.profile_image
        details['instructor_id'] = instructor.id
        instructor_details.append(details)
    context['instructor_details'] = instructor_details
    context['instructor_headers'] = INSTRUCTOR_DISPLAY_HEADER
    context['no_sort_columns'] = NO_SORT_COLUMNS
    return render_to_response('admin_dash/management/instructor_form.html', context)


@login_required
@site_administrator_only
def add_instructor(request, template_name='admin_dash/management/instructor_create_form.html'):
    form = InstructorForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        instructor = form.save(commit=False)
        instructor.save()
        return redirect(reverse('show-instructor'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def update_instructor(request, pk, template_name='admin_dash/management/instructor_create_form.html'):
    instructor = get_object_or_404(Instructor, pk=pk)
    form = InstructorForm(request.POST or None, instance=instructor)
    if form.is_valid():
        form.save()
        return redirect(reverse('show-instructor'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def delete_instructor(request, pk):
    instructor = get_object_or_404(Instructor, pk=pk)
    instructor.delete()
    return redirect(reverse('show-instructor'))


@login_required
@site_administrator_only
def show_institution(request):
    """
    Display all the institution.
    """
    INSTITUTION_DISPLAY_HEADER = ['Name', 'Website URL', 'Logo', 'Delete?']
    NO_SORT_COLUMNS = ['Delete?', 'Logo']
    institutions = Institution.objects.all()
    context = {}
    institution_details = []
    for institution in institutions:
        details = OrderedDict()
        details['institution_name'] = institution.name
        details['institution_website_url'] = institution.website_url
        details['institution_logo'] = institution.logo
        details['institution_id'] = institution.id
        institution_details.append(details)
    context['institution_details'] = institution_details
    context['institution_headers'] = INSTITUTION_DISPLAY_HEADER
    context['no_sort_columns'] = NO_SORT_COLUMNS
    return render_to_response('admin_dash/management/institution_form.html', context)


@login_required
@site_administrator_only
def add_institution(request, template_name='admin_dash/management/institution_create_form.html'):
    form = InstitutionForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        institution = form.save(commit=False)
        institution.save()
        return redirect(reverse('show-institution'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def update_institution(request, pk, template_name='admin_dash/management/institution_create_form.html'):
    institution = get_object_or_404(Institution, pk=pk)
    form = InstitutionForm(request.POST or None, instance=institution)
    if form.is_valid():
        form.save()
        return redirect(reverse('show-institution'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def delete_institution(request, pk):
    institution = get_object_or_404(Institution, pk=pk)
    institution.delete()
    return redirect(reverse('show-institution'))


@login_required
@site_administrator_only
def show_signatories(request):
    """
    Display all the signatories.
    """
    SIGNATORIES_DISPLAY_HEADER = ['Name', 'Title', 'Institution', 'Program', 'Signature', 'Delete?']
    NO_SORT_COLUMNS = ['Delete?', 'Signature']
    signatories = ProgramCertificateSignatories.objects.all()
    context = {}
    signatories_details = []
    for signature in signatories:
        details = OrderedDict()
        details['signatories_name'] = signature.name
        details['signatories_title'] = signature.title
        details['signatories_institution'] = signature.institution.name
        details['signatories_program'] = signature.program.name
        details['signatories_signature_image'] = signature.signature_image
        details['signatories_id'] = signature.id
        signatories_details.append(details)
    context['signatories_details'] = signatories_details
    context['signatories_headers'] = SIGNATORIES_DISPLAY_HEADER
    context['no_sort_columns'] = NO_SORT_COLUMNS
    return render_to_response('admin_dash/management/signatories_form.html', context)


@login_required
@site_administrator_only
def add_signatories(request, template_name='admin_dash/management/signatories_create_form.html'):
    form = ProgramCertificateSignatoriesForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        signatories = form.save(commit=False)
        signatories.save()
        return redirect(reverse('show-signatories'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def update_signatories(request, pk, template_name='admin_dash/management/signatories_create_form.html'):
    signatories = get_object_or_404(ProgramCertificateSignatories, pk=pk)
    form = ProgramCertificateSignatoriesForm(request.POST or None, instance=signatories)
    if form.is_valid():
        form.save()
        return redirect(reverse('show-signatories'))
    return render_to_response(template_name, {'form': form})


@login_required
@site_administrator_only
def delete_signatories(request, pk):
    signatories = get_object_or_404(ProgramCertificateSignatories, pk=pk)
    signatories.delete()
    return redirect(reverse('show-signatories'))
