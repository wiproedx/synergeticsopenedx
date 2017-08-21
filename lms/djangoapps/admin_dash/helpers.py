import string
import re
import smtplib
import logging
from boto.exception import BotoServerError

from django.core.mail.message import EmailMessage
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from edxmako.shortcuts import render_to_string
from course_modes.models import CourseMode
from student.models import UserProfile
from student.models import CourseAccessRole
from opaque_keys.edx.keys import CourseKey
from shoppingcart.models import Coupon
from openedx.core.djangoapps.micro_masters.models import ProgramCoupon, Program

log = logging.getLogger("admin_dash")


def get_num_students():
    return User.objects.filter(is_active=True).count()


def get_courses():
    return CourseOverview.objects.all()


def get_num_courses():
    courses = get_courses()
    return len(courses)


def get_num_instructors():
    instructors = []
    courses = get_courses()
    for course in courses:
        team_members = CourseAccessRole.objects.filter(course_id=course.id)
        for member in team_members:
            if member.user not in instructors:
                instructors.append(member.user)

    return len(instructors)


def get_course_overview(course_id):
    try:
        course_overview = CourseOverview.objects.get(id=course_id)
        return course_overview
    except ObjectDoesNotExist:
        return None


def get_course_price(course):
    course_mode_details, created = CourseMode.objects.get_or_create(
        course_id=course.id)
    if created:
        course_mode_details.mode_slug = course_mode_details.mode_display_name = 'honor'
        course_mode_details.save()
    registration_price = course_mode_details.min_course_price_for_currency(
        course.id,
        settings.PAID_COURSE_REGISTRATION_CURRENCY[0]
    )
    if registration_price > 0:
        currency = settings.PAID_COURSE_REGISTRATION_CURRENCY[0]
        course_price = ("{price}").format(price=registration_price)
    else:
        course_price = 'FREE'
    return course_price


def get_user_profile(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
        return user_profile
    except ObjectDoesNotExist:
        return None


def send_user_credentials(user, details):
    from_email = configuration_helpers.get_value(
        'email_from_address', settings.DEFAULT_FROM_EMAIL)
    to_email = [details.get('email', '')]
    subject = 'Login Credentails'
    context = details
    mail_body = render_to_string(
        'admin_dash/management/credentails_mail_body.txt', context)
    email = EmailMessage(
        subject=subject,
        body=mail_body,
        from_email=from_email,
        to=to_email
    )
    email.send()
    log.info("Mail Sent Successfully to the user %s",
             str(details.get('email', '')))


def user_other_settings(user_id, details):
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        if details.get('admin', '') == unicode('true'):
            user.is_superuser = True
            user.is_staff = True
            user_profile = get_user_profile(user)
            user_profile.site_manager = True
            user_profile.save()
        if details.get('instructor', '') == unicode('true'):
            user.is_staff = True
        if details.get('site_admin', '') == unicode('true'):
            user_profile = get_user_profile(user)
            user_profile.site_manager = True
            user_profile.save()
        user.save()
        if details.get('mail_credentials', '') == unicode('true'):
            send_user_credentials(user, details)
        return {
            'success': True,
            'error_msg': ''
        }
    except (smtplib.SMTPException, BotoServerError):
        return {
            'success': False,
            'error_msg': 'Error while sending mail.'
        }
    except Exception as error:
        return {
            'success': False,
            'error_msg': error.message
        }


def get_image_url(status):
    site_name = settings.SITE_NAME
    if status == 'active':
        url = 'http://' + str(site_name) + \
            '/static/' + settings.DEFAULT_SITE_THEME + 'admin_dash/images/icon-yes.gif'
    else:
        url = 'http://' + str(site_name) + \
            '/static/' + settings.DEFAULT_SITE_THEME + 'admin_dash/images/icon-no.gif'
    return url


def get_coupons():
    coupons = Coupon.objects.all()
    return coupons


def update_price(course_id, course_price):
    try:
        course_key = CourseKey.from_string(course_id)
        course_mode = CourseMode.objects.get(course_id=course_key)
        course_mode.min_price = course_price
        course_mode.save()
        return {
            'success': True,
            'message': ''
        }
    except ObjectDoesNotExist:
        return {
            'success': False,
            'message': 'Invalid Key'
        }


def validate_coupon_details(details):
    discount = int(details.get('discount', 0))
    course_id = details.get('course_id')
    valid_discount = True if discount >= 0 and discount <= 100 else False
    try:
        course_key = CourseKey.from_string(course_id)
    except Exception as error:
        return {
            'valid': False
        }
    if valid_discount:
        return {
            'valid': True,
            'course_key': course_key
        }
    return {
        'valid': False
    }


def get_num_programs():
    programs = Program.objects.all()
    return programs


def get_program_coupons():
    coupons = ProgramCoupon.objects.all()
    return coupons


def validate_program_coupon_details(details):
    discount = int(details.get('discount', 0))
    program_id = details.get('program_id')
    valid_discount = True if discount >= 0 and discount <= 100 else False
    try:
        program = Program.objects.get(id=program_id)
    except Exception as error:
        return {
            'valid': False
        }
    if valid_discount:
        return {
            'valid': True,
            'program_id': program
        }
    return {
        'valid': False
    }


def get_programe_price(program):
    price = program.price
    if price > 0:
        currency = settings.PAID_COURSE_REGISTRATION_CURRENCY[0]
        course_price = ("{price}").format(price=price)
    else:
        course_price = 'FREE'
    return course_price


def program_price_update(program_id, program_price):
    try:
        program = Program.objects.get(id=program_id)
        program.price = program_price
        program.save()
        return {
            'success': True,
            'message': ''
        }
    except ObjectDoesNotExist:
        return {
            'success': False,
            'message': 'Invalid Key'
        }
