"""
Django models for programs.
"""
import pytz
import hashlib
import time
import json
import logging
import smtplib
import uuid
import StringIO
from io import BytesIO
# this is a super-class of SESError and catches connection errors
from boto.exception import BotoServerError
from decimal import Decimal
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.core.mail.message import EmailMessage
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.validators import URLValidator
from django_extensions.db.models import TimeStampedModel
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _, ugettext_noop

from edxmako.shortcuts import render_to_string
from util.models import CompressedTextField
from student.models import CourseEnrollment
from shoppingcart.pdf import PDFInvoice
from shoppingcart.exceptions import MultipleCouponsNotAllowedException
from openedx.core.djangoapps.xmodule_django.models import CourseKeyField
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

log = logging.getLogger("micro_masters")

ORDER_STATUSES = (
    # The user is selecting what he/she wants to purchase.
    ('initiate', 'initiate'),

    # The user has successfully purchased the items in the order.
    ('purchased', 'purchased'),

    # The user's order has been refunded.
    ('refunded', 'refunded'),
)


def content_file_name(instance, filename):
    hash_ = hashlib.sha1()
    hash_.update(str(time.time()))
    name = 'programs/content-' + hash_.hexdigest()[:20] + '_' + filename
    return name


class Courses(TimeStampedModel):
    """
    Model for storing course id and name.
    """
    course_key = CourseKeyField(db_index=True, max_length=255)
    name = models.CharField(max_length=200)

    class Meta:
        app_label = 'micro_masters'
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'

    @classmethod
    def create_or_update_from_course_overview(cls, course_overview):
        title = course_overview.display_name
        course_key = course_overview.id
        try:
            course = cls.objects.get(course_key=course_key)
            course.name = title
            course.save()
        except cls.DoesNotExist:
            cls.objects.create(
                course_key=course_key,
                name=title
            )

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()


class Subject(TimeStampedModel):
    """
    Model for storing subject.
    """
    name = models.CharField(max_length=200, unique=True)
    mark_as_popular = models.BooleanField(default=0)

    class Meta:
        app_label = 'micro_masters'
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()


class Language(TimeStampedModel):
    """
    Model for storing language.
    """
    name = models.CharField(max_length=200, unique=True)
    code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        app_label = 'micro_masters'
        verbose_name = 'Language'
        verbose_name_plural = 'Language'

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()


class Institution(TimeStampedModel):
    """
    Model for storing Institution.
    """
    name = models.CharField(max_length=200, unique=True)
    website_url = models.TextField(
        validators=[URLValidator()], blank=True, null=True)
    logo = models.ImageField(max_length=200, upload_to=content_file_name)

    def image_tag(self):
        return u'<img src="%s" width="50" height="50" />' % self.logo.url
    image_tag.short_description = 'Logo'
    image_tag.allow_tags = True

    class Meta:
        app_label = 'micro_masters'
        verbose_name = 'Institution'
        verbose_name_plural = 'Institution'

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()


class Instructor(TimeStampedModel):
    """
    Model for storing Instructor.
    """
    name = models.CharField(max_length=200, null=True, blank=True)
    designation = models.CharField(max_length=200, null=True, blank=True)
    profile_image = models.ImageField(
        max_length=200, upload_to=content_file_name)
    institution = models.ForeignKey(Institution, null=True, blank=True)

    def image_tag(self):
        return u'<img src="%s" width="50" height="50" />' % self.profile_image.url
    image_tag.short_description = 'Profile image'
    image_tag.allow_tags = True

    class Meta:
        app_label = 'micro_masters'
        verbose_name = 'Instructor'
        verbose_name_plural = 'Instructor'

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()


class Program(TimeStampedModel):
    """
    Model for storing programs.
    """

    overview = """<section class="overview">
        <h3 class="overview-title">
            Dummay text.
        </h3>
        <div class="overview-content">
            <p>
                This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in paragraph tags.
            </p>
        </div>
    </section>
    <section class="job-outlook">
        <h3>About This Path</h3>
        <ul>
            <li>
                This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in li tags.
            </li>
            <li>
                This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in li tags.
            </li>
            <li>
                This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in li tags.
            </li>
        </ul>
    </section>
    <section class="expected-learning">
        <h3>Overview:</h3>
        <ul>
            <li>This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in li tags.</li>
            <li>This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in li tags.</li>
            <li>This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in li tags.</li>
            <li>How to do full-stack software development using an agile approach in a pair or team</li>
            <li>This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in li tags.</li>
        </ul>
    </section>
    """

    name = models.CharField(max_length=200, unique=True)
    start = models.DateField(null=True)
    end = models.DateField(null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    price = models.IntegerField()
    banner_image = models.ImageField(
        max_length=200, upload_to=content_file_name)
    introductory_video = models.FileField(upload_to=content_file_name)
    overview = models.TextField(null=True, blank=True, default=overview)
    sample_certificate_pdf = models.FileField(upload_to=content_file_name)
    average_length = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text="e.g. 6-7 weeks per course"
    )
    effort = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text="e.g. 8-10 hours per week, per course"
    )
    language = models.ForeignKey(
        Language, related_name='program_language', null=True, blank=True)
    video_transcripts = models.ForeignKey(
        Language, related_name='transcript_language', null=True, blank=True)
    subject = models.ForeignKey(Subject, null=True, blank=True)
    institution = models.ForeignKey(Institution, null=True, blank=True)
    instructors = models.ManyToManyField(Instructor)
    courses = models.ManyToManyField(Courses)

    def image_tag(self):
        return u'<img src="%s" width="150" height="50" />' % self.banner_image.url
    image_tag.short_description = 'Banner image'
    image_tag.allow_tags = True

    class Meta:
        app_label = 'micro_masters'
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()

    @classmethod
    def course_has_part_of_programs(cls, course_id):
        """
        Check this course is part of programs
        """
        programs = cls.objects.all()
        course_programs_details = []
        for program in programs:
            if program.start <= datetime.now(pytz.UTC).date():
                for course in program.courses.select_related():
                    if str(course.course_key) == course_id:
                        program_about = reverse('openedx.core.djangoapps.micro_masters.views.program_about', args=str(program.id))
                        course_programs_details.append({
                            program.name: program_about
                        })
                        break
                        # return True
        return course_programs_details


class ProgramOrder(TimeStampedModel):
    """Storing Program Order"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    program = models.ForeignKey(Program)
    item_name = models.CharField(max_length=200, blank=True)
    item_price = models.IntegerField(
        blank=True,
        null=True,
        default=0
    )
    discounted_price = models.IntegerField(
        blank=True,
        null=True,
        default=0
    )
    status = models.CharField(
        max_length=32, default='initiate', choices=ORDER_STATUSES)
    processor_response_json = CompressedTextField(
        verbose_name='Processor Response JSON', blank=True, null=True)
    purchase_time = models.DateTimeField(null=True, blank=True)
    refunded_time = models.DateTimeField(null=True, blank=True)
    bill_to_first = models.CharField(max_length=64, blank=True)
    bill_to_last = models.CharField(max_length=64, blank=True)
    bill_to_street1 = models.CharField(max_length=128, blank=True)
    bill_to_street2 = models.CharField(max_length=128, blank=True)
    bill_to_city = models.CharField(max_length=64, blank=True)
    bill_to_state = models.CharField(max_length=8, blank=True)
    bill_to_postalcode = models.CharField(max_length=16, blank=True)
    bill_to_country = models.CharField(max_length=64, blank=True)

    class Meta:
        app_label = 'micro_masters'
        verbose_name = 'Program Order'
        verbose_name_plural = 'Program Order'

    @property
    def processor_response(self):
        if self.processor_response_json:
            return json.loads(self.processor_response_json)

    def __unicode__(self):
        return self.user.username

    def __repr__(self):
        return self.__unicode__()

    @classmethod
    def get_or_create_order(cls, user, program):
        """
        if not then create order for user

        user: user object
        program: program object

        return
            order object
        """
        cart_order, _created = ProgramOrder.objects.get_or_create(
            user=user, program=program, status='initiate')
        cart_order.item_name = cart_order.program.name
        cart_order.item_price = cart_order.program.price
        cart_order.save()
        return cart_order

    def generate_pdf_receipt(self):
        """
        Generates the pdf receipt for the order
        and returns the pdf_buffer.
        """
        items_data = []

        items_data.append({
            'item_description': self.item_name,
            'quantity': 1,
            'list_price': self.item_price,
            'discount': self.item_price - self.discounted_price,
            'item_total': self.item_price
        })
        pdf_buffer = BytesIO()

        PDFInvoice(
            items_data=items_data,
            item_id=str(self.id),
            date=self.purchase_time,
            is_invoice=False,
            total_cost=self.item_price,
            payment_received=self.item_price,
            balance=0
        ).generate_pdf(pdf_buffer)
        return pdf_buffer

    def send_confirmation_emails(self, pdf_file, site_name):
        """
        send confirmation e-mail
        """
        recipient_list = [(self.user.username, self.user.email,
                           'user')]  # pylint: disable=no-member

        subject = _("Order Payment Confirmation")

        dashboard_url = '{base_url}{dashboard}'.format(
            base_url=site_name,
            dashboard=reverse('dashboard')
        )
        try:
            from_address = configuration_helpers.get_value(
                'email_from_address',
                settings.PAYMENT_SUPPORT_EMAIL
            )
            # Send a unique email for each recipient. Don't put all email
            # addresses in a single email.
            for recipient in recipient_list:
                message = render_to_string(
                    'micro_masters/emails/order_confirmation_email.txt',
                    {
                        'order': self,
                        'recipient_name': recipient[0],
                        'recipient_type': recipient[2],
                        'site_name': site_name,
                        'dashboard_url': dashboard_url,
                        'currency_symbol': settings.PAID_COURSE_REGISTRATION_CURRENCY[1],
                        'order_placed_by': '{username} ({email})'.format(
                            username=self.user.username, email=self.user.email
                        ),
                        'has_billing_info': settings.FEATURES['STORE_BILLING_INFO'],
                        'platform_name': configuration_helpers.get_value('platform_name', settings.PLATFORM_NAME),
                        'payment_support_email': configuration_helpers.get_value(
                            'payment_support_email', settings.PAYMENT_SUPPORT_EMAIL,
                        ),
                        'payment_email_signature': configuration_helpers.get_value('payment_email_signature'),
                    }
                )
                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=from_address,
                    to=[recipient[1]]
                )

                if pdf_file is not None:
                    email.attach(u'Receipt.pdf',
                                 pdf_file.getvalue(), 'application/pdf')
                else:
                    file_buffer = StringIO.StringIO(
                        _('pdf download unavailable right now, please contact support.'))
                    email.attach(u'pdf_not_available.txt',
                                 file_buffer.getvalue(), 'text/plain')
                email.send()
        # sadly need to handle diff. mail backends individually
        except (smtplib.SMTPException, BotoServerError):
            log.error('Failed sending confirmation e-mail for order %d', self.id)

    def purchase(self, first='', last='', street1='', street2='', city='', state='', postalcode='',
                 country='', processor_reply_dump=''):
        """
        Call to mark this order as purchased.  Iterates through its OrderItems and calls
        their purchased_callback

        `first` - first name of person billed (e.g. John)
        `last` - last name of person billed (e.g. Smith)
        `street1` - first line of a street address of the billing address (e.g. 11 Cambridge Center)
        `street2` - second line of a street address of the billing address (e.g. Suite 101)
        `city` - city of the billing address (e.g. Cambridge)
        `state` - code of the state, province, or territory of the billing address (e.g. MA)
        `postalcode` - postal code of the billing address (e.g. 02142)
        `country` - country code of the billing address (e.g. US)
        `processor_reply_dump` - all the parameters returned by the processor

        """
        if self.status == 'purchased':
            log.error(
                u"`purchase` method called on order {}, but order is already purchased.".format(
                    self.id)  # pylint: disable=no-member
            )
            return
        self.status = 'purchased'
        self.purchase_time = datetime.now(pytz.utc)
        self.bill_to_first = first
        self.bill_to_last = last
        self.bill_to_city = city
        self.bill_to_state = state
        self.bill_to_country = country
        self.bill_to_postalcode = postalcode
        self.processor_response_json = processor_reply_dump
        self.bill_to_street1 = street1
        self.bill_to_street2 = street2

        # save these changes on the order, then we can tell when we are in an
        # inconsistent state
        self.save()
        # this should return all of the objects with the correct types of the
        # subclasses

        site_name = configuration_helpers.get_value(
            'SITE_NAME', settings.SITE_NAME)

        try:
            pdf_file = self.generate_pdf_receipt()
        except Exception:  # pylint: disable=broad-except
            log.exception('Exception at creating pdf file.')
            pdf_file = None

        try:
            self.send_confirmation_emails(pdf_file, site_name)
        except Exception:  # pylint: disable=broad-except
            # Catch all exceptions here, since the Django view implicitly
            # wraps this in a transaction.  If the order completes successfully,
            # we don't want to roll back just because we couldn't send
            # the confirmation email.
            log.exception(
                'Error occurred while sending payment confirmation email')


class ProgramEnrollment(TimeStampedModel):
    """Storing Program Enrollment"""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=0)

    class Meta:
        app_label = 'micro_masters'
        verbose_name = 'Program Enrollment'
        verbose_name_plural = 'Program Enrollment'

    @classmethod
    def is_enrolled(cls, user, program_id):
        if not user.is_authenticated():
            return False
        try:
            record = cls.objects.get(user=user, program__id=program_id)
            return record.is_active
        except cls.DoesNotExist:
            return False

    @classmethod
    def enroll(cls, user, program_id):
        try:
            program = Program.objects.get(pk=program_id)
        except:
            return False

        change_course_enrollment, _create = cls.objects.get_or_create(
            user=user,
            program=program
        )
        change_course_enrollment.is_active = True
        change_course_enrollment.save()

        for course in program.courses.select_related():
            CourseEnrollment.enroll(user, course.course_key)
        return True

    @classmethod
    def unenroll(cls, user, program_id):
        try:
            program = Program.objects.get(pk=program_id)
        except:
            return False

        for course in program.courses.select_related():
            CourseEnrollment.unenroll(user, course.course_key)
        change_course_enrollment = cls.objects.get(user=user, program=program)
        change_course_enrollment.is_active = False
        change_course_enrollment.save()

        return True


class ProgramCoupon(TimeStampedModel):
    """
    This table contains coupon codes
    A user can get a discount offer on course if provide coupon code for programs
    """
    class Meta():
        app_label = 'micro_masters'
        verbose_name = 'Program Coupon'
        verbose_name_plural = 'Program Coupons'

    code = models.CharField(max_length=32, db_index=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    program = models.ForeignKey(Program)
    percentage_discount = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    expiration_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return "[Coupon] code: {} program: {}".format(self.code, self.program.name)

    @property
    def display_expiry_date(self):
        """
        return the coupon expiration date in the readable format
        """
        return (self.expiration_date - timedelta(days=1)).strftime("%B %d, %Y") if self.expiration_date else None


class ProgramCouponRedemption(TimeStampedModel):
    """
    This table contain coupon redemption info of programs
    """
    class Meta():
        app_label = 'micro_masters'
        verbose_name = 'Program Coupon Redemption'
        verbose_name_plural = 'Program Coupon Redemptions'

    order = models.ForeignKey(ProgramOrder, db_index=True)
    user = models.ForeignKey(User, db_index=True)
    coupon = models.ForeignKey(ProgramCoupon, db_index=True)

    @classmethod
    def get_discount_price(cls, percentage_discount, value):
        """
        return discounted price against coupon
        """
        discount = Decimal("{0:.2f}".format(Decimal(percentage_discount / 100.00) * value))
        return value - discount

    @classmethod
    def add_coupon_redemption(cls, coupon, order):
        """
        add coupon info into coupon_redemption model
        """
        is_redemption_applied = False
        coupon_redemptions = cls.objects.filter(order=order, user=order.user)
        for coupon_redemption in coupon_redemptions:
            if coupon_redemption.coupon.code != coupon.code or coupon_redemption.coupon.id == coupon.id:
                log.exception(
                    u"Coupon redemption already exist for user '%s' against order id '%s'",
                    order.user.username,
                    order.id,
                )
                raise MultipleCouponsNotAllowedException

        if order.program.id == coupon.program.id:
            coupon_redemption = cls(order=order, user=order.user, coupon=coupon)
            coupon_redemption.save()
            discount_price = cls.get_discount_price(coupon.percentage_discount, order.item_price)
            order.discounted_price = discount_price
            order.save()
            log.info(
                u"Discount generated for user %s against order id '%s'",
                order.user.username,
                order.id,
            )
            is_redemption_applied = True
            return is_redemption_applied
        return is_redemption_applied

    @classmethod
    def remove_coupon_redemption_from_cart(cls, user, order):
        """
        This method delete coupon redemption
        """
        coupon_redemption = cls.objects.filter(user=user, order=order)
        if coupon_redemption:
            coupon_redemption.delete()
            log.info(u'Coupon redemption entry removed for user %s for order %s', user, order.id)


class ProgramCertificateSignatories(TimeStampedModel):
    """
    This table Certificate Signatories of programs
    """
    class Meta():
        app_label = 'micro_masters'
        verbose_name = 'Program Certificate Signatories'
        verbose_name_plural = 'Program Certificate Signatories'

    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=150,
        help_text='The name of this signatory as it should appear on certificates.'
    )
    title = models.CharField(
        max_length=100,
        help_text='Titles more than 100 characters may prevent students from printing their certificate on a single page.'
    )
    institution = models.ForeignKey(
        Institution,
        help_text='The organization that this signatory belongs to, as it should appear on certificates.'
    )
    signature_image = models.ImageField(
        max_length=200,
        upload_to=content_file_name,
    )

    def image_tag(self):
        return u'<img src="%s" width="150" height="50" />' % self.signature_image.url
    image_tag.short_description = 'Signature image'
    image_tag.allow_tags = True

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()


class ProgramGeneratedCertificate(TimeStampedModel):
    """
    This table storing Generated Certificate of user
    """
    class Meta():
        app_label = 'micro_masters'
        verbose_name = 'Program Generated Certificate'
        verbose_name_plural = 'Program Generated Certificate'

    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    verify_uuid = models.CharField(max_length=32, blank=True, default='', db_index=True)
    issued = models.BooleanField(default=False)

    def __unicode__(self):
        return self.program.name

    def __repr__(self):
        return self.__unicode__()

    @classmethod
    def create_user_certificate(cls, user, program, issued=False):
        if issued:
            program_certy, _created = cls.objects.get_or_create(
                user=user,
                program=program,
            )
            if _created:
                program_certy.verify_uuid = uuid.uuid4().hex
            program_certy.issued = issued
            program_certy.save()
            return program_certy
        else:
            try:
                program_certy = cls.objects.get(
                    user=user,
                    program=program,
                )
                program_certy.issued = issued
                program_certy.save()
            except Exception, e:
                return False
        return False
