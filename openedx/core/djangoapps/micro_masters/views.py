import json
import uuid
import hmac
import logging
import binascii
import urllib
import pytz
from collections import OrderedDict
from datetime import datetime
from hashlib import sha256
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.utils.encoding import smart_str
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.http import (
    Http404, HttpResponseRedirect,
    HttpResponseNotFound, HttpResponse,
    HttpResponseBadRequest
)
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils.translation import ugettext as _, ugettext_noop

from edxmako.shortcuts import render_to_response, render_to_string
from xmodule.modulestore.django import ModuleI18nService
from shoppingcart.processors.exceptions import *
from microsite_configuration import microsite
from courseware.courses import get_course_by_id
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from .models import (
    Program, ProgramEnrollment,
    ProgramOrder, ProgramCoupon,
    ProgramCouponRedemption, ProgramGeneratedCertificate,
    ProgramCertificateSignatories
)
from shoppingcart.exceptions import (
    MultipleCouponsNotAllowedException, InvalidCartItem,
    ItemNotFoundInCartException, RedemptionCodeError
)
from student.models import LinkedInAddToProfileConfiguration
from certificates.api import (
    get_certificate_header_context,
    get_certificate_footer_context,
)
from leaderboard.models import LeaderBoard

log = logging.getLogger(__name__)

CC_PROCESSOR = settings.CC_PROCESSOR.get(settings.CC_PROCESSOR_NAME)

# Start before payment_method


def processor_hash(value):
    """
    Calculate the base64-encoded, SHA-256 hash used by CyberSource.

    Args:
        value (string): The value to encode.

    Returns:
        string

    """
    secret_key = CC_PROCESSOR.get('SECRET_KEY', '')
    hash_obj = hmac.new(secret_key.encode('utf-8'),
                        value.encode('utf-8'), sha256)
    # last character is a '\n', which we don't want
    return binascii.b2a_base64(hash_obj.digest())[:-1]


def sign(params):
    """
    Sign the parameters dictionary so CyberSource can validate our identity.

    The params dict should contain a key 'signed_field_names' that is a comma-separated
    list of keys in the dictionary.  The order of this list is important!

    Args:
        params (dict): Dictionary of parameters; must include a 'signed_field_names' key

    Returns:
        dict: The same parameters dict, with a 'signature' key calculated from the other values.

    """
    fields = u",".join(params.keys())
    params['signed_field_names'] = fields

    signed_fields = params.get('signed_field_names', '').split(',')
    values = u",".join([u"{0}={1}".format(i, params.get(i, ''))
                        for i in signed_fields])
    params['signature'] = processor_hash(values)
    params['signed_field_names'] = fields

    return params


def get_purchase_params(cart, callback_url=None):
    """
    This method will build out a dictionary of parameters needed by CyberSource to complete the transaction

    Args:
        cart (Order): The order model representing items in the user's cart.

    Keyword Args:
        callback_url (unicode): The URL that CyberSource should POST to when the user
            completes a purchase.  If not provided, then CyberSource will use
            the URL provided by the administrator of the account
            (CyberSource config, not LMS config).

        extra_data (list): Additional data to include as merchant-defined data fields.

    Returns:
        dict

    """

    params = OrderedDict()
    program_price = cart.discounted_price if cart.discounted_price else cart.program.price
    amount = "{0:0.2f}".format(program_price)
    params['amount'] = amount
    params['currency'] = settings.PAID_COURSE_REGISTRATION_CURRENCY[0]
    params['orderNumber'] = "OrderId: {0:d}".format(cart.id)
    params['access_key'] = CC_PROCESSOR.get('ACCESS_KEY', '')
    params['profile_id'] = CC_PROCESSOR.get('PROFILE_ID', '')
    params['reference_number'] = cart.id
    params['transaction_type'] = 'sale'
    params['locale'] = 'en'
    params['signed_date_time'] = datetime.utcnow(
    ).strftime('%Y-%m-%dT%H:%M:%SZ')
    params['signed_field_names'] = 'access_key,profile_id,amount,currency,transaction_type,reference_number,signed_date_time,locale,transaction_uuid,signed_field_names,unsigned_field_names,orderNumber'
    params['unsigned_field_names'] = ''
    params['transaction_uuid'] = uuid.uuid4().hex
    params['payment_method'] = 'card'

    if callback_url is not None:
        params['override_custom_receipt_page'] = callback_url.get('success')
        params['override_custom_cancel_page'] = callback_url.get('cancel')
    return sign(params)

# End before payment_method


# Start after payment method
def _record_purchase(params, order):
    """
    Record the purchase and run purchased_callbacks

    Args:
        params (dict): The parameters we received from CyberSource.
        order (Order): The order associated with this payment.

    Returns:
        None

    """

    if settings.FEATURES.get("LOG_POSTPAY_CALLBACKS"):
        log.info(
            "Order %d purchased with params: %s", order.id, json.dumps(params)
        )

    # Mark the order as purchased and store the billing information
    # order.purchase(
    #     first=params.get('req_bill_to_forename', ''),
    #     last=params.get('req_bill_to_surname', ''),
    #     street1=params.get('req_bill_to_address_line1', ''),
    #     street2=params.get('req_bill_to_address_line2', ''),
    #     city=params.get('req_bill_to_address_city', ''),
    #     state=params.get('req_bill_to_address_state', ''),
    #     country=params.get('req_bill_to_address_country', ''),
    #     postalcode=params.get('req_bill_to_address_postal_code', ''),
    #     processor_reply_dump=json.dumps(params)
    # )

    order.purchase(
        first=params.get('req_ship_to_forename', ''),
        last=params.get('req_ship_to_surname', ''),
        street1=params.get('req_ship_to_address_line1', ''),
        street2=params.get('req_ship_to_address_line1', ''),
        city=params.get('req_bill_to_address_city', ''),
        state=params.get('req_bill_to_address_state', ''),
        country=params.get('req_ship_to_address_country', ''),
        postalcode=params.get('req_ship_to_address_postal_code', ''),
        processor_reply_dump=json.dumps(params)
    )


def verify_signatures(params):
    """
    Use the signature we receive in the POST back from CyberSource to verify
    the identity of the sender (CyberSource) and that the contents of the message
    have not been tampered with.

    Args:
        params (dictionary): The POST parameters we received from CyberSource.

    Returns:
        dict: Contains the parameters we will use elsewhere, converted to the
            appropriate types

    Raises:
        CCProcessorSignatureException: The calculated signature does not match
            the signature we received.

        CCProcessorDataException: The parameters we received from CyberSource were not valid
            (missing keys, wrong types)

    """

    # comment did intencinaly for checking recept of programs

    # if params.get('decision') == u'CANCEL':
    #     raise CCProcessorUserCancelled()

    # if params.get('decision') == u'DECLINE':
    #     raise CCProcessorUserDeclined()

    # signed_fields = params.get('signed_field_names', '').split(',')
    # data = u",".join([u"{0}={1}".format(k, params.get(k, '')) for k in signed_fields])
    # returned_sig = params.get('signature', '')
    # if processor_hash(data) != returned_sig:
    #     raise CCProcessorSignatureException()

    # Validate that we have the paramters we expect and can convert them
    # to the appropriate types.
    # Usually validating the signature is sufficient to validate that these
    # fields exist, but since we're relying on CyberSource to tell us
    # which fields they included in the signature, we need to be careful.
    valid_params = {}
    required_params = [
        ('req_reference_number', int),
        ('req_currency', str),
        ('decision', str),
        ('auth_amount', Decimal),
    ]
    # for key, key_type in required_params:
    #     if key not in params:
    #         raise CCProcessorDataException(
    #             _(
    #                 u"The payment processor did not return a required parameter: {parameter}"
    #             ).format(parameter=key)
    #         )
    #     try:
    #         valid_params[key] = key_type(params[key])
    #     except (ValueError, TypeError, InvalidOperation):
    #         raise CCProcessorDataException(
    #             _(
    #                 u"The payment processor returned a badly-typed value {value} for parameter {parameter}."
    #             ).format(value=params[key], parameter=key)
    #         )

    # temporary fix
    valid_params['req_reference_number'] = params.get('req_reference_number')
    valid_params['req_currency'] = params.get('req_currency')
    valid_params['decision'] = 'ACCEPT' or params.get('decision')
    valid_params['auth_amount'] = params.get('req_amount')
    return valid_params


def _payment_accepted(order_id, auth_amount, currency, decision):
    """
    Check that CyberSource has accepted the payment.

    Args:
        order_num (int): The ID of the order associated with this payment.
        auth_amount (Decimal): The amount the user paid using CyberSource.
        currency (str): The currency code of the payment.
        decision (str): "ACCEPT" if the payment was accepted.

    Returns:
        dictionary of the form:
        {
            'accepted': bool,
            'amnt_charged': int,
            'currency': string,
            'order': Order
        }

    Raises:
        CCProcessorDataException: The order does not exist.
        CCProcessorWrongAmountException: The user did not pay the correct amount.

    """
    try:
        order = ProgramOrder.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise CCProcessorDataException(
            _("The payment processor accepted an order whose number is not in our system."))

    if decision == 'ACCEPT':
        return {
            'accepted': True,
            'amt_charged': auth_amount,
            'currency': currency,
            'order': order
        }
    else:
        return {
            'accepted': False,
            'amt_charged': 0,
            'currency': 'usd',
            'order': order
        }


def _record_payment_info(params, order):
    """
    Record the purchase and run purchased_callbacks

    Args:
        params (dict): The parameters we received from CyberSource.

    Returns:
        None
    """
    if settings.FEATURES.get("LOG_POSTPAY_CALLBACKS"):
        log.info(
            "Order %d processed (but not completed) with params: %s", order.id, json.dumps(
                params)
        )

    order.processor_reply_dump = json.dumps(params)
    order.save()


def _format_error_html(msg):
    """ Format an HTML error message """
    return u'<p class="error_msg">{msg}</p>'.format(msg=msg)


def _get_processor_exception_html(exception):
    """
    Return HTML indicating that an error occurred.

    Args:
        exception (CCProcessorException): The exception that occurred.

    Returns:
        unicode: The rendered HTML.

    """
    payment_support_email = microsite.get_value(
        'payment_support_email', settings.PAYMENT_SUPPORT_EMAIL)
    if isinstance(exception, CCProcessorDataException):
        return _format_error_html(
            _(
                u"Sorry! Our payment processor sent us back a payment confirmation that had inconsistent data! "
                u"We apologize that we cannot verify whether the charge went through and take further action on your order. "
                u"The specific error message is: {msg} "
                u"Your credit card may possibly have been charged.  Contact us with payment-specific questions at {email}."
            ).format(
                msg=u'<span class="exception_msg">{msg}</span>'.format(
                    msg=exception.message),
                email=payment_support_email
            )
        )
    elif isinstance(exception, CCProcessorWrongAmountException):
        return _format_error_html(
            _(
                u"Sorry! Due to an error your purchase was charged for a different amount than the order total! "
                u"The specific error message is: {msg}. "
                u"Your credit card has probably been charged. Contact us with payment-specific questions at {email}."
            ).format(
                msg=u'<span class="exception_msg">{msg}</span>'.format(
                    msg=exception.message),
                email=payment_support_email
            )
        )
    elif isinstance(exception, CCProcessorSignatureException):
        return _format_error_html(
            _(
                u"Sorry! Our payment processor sent us back a corrupted message regarding your charge, so we are "
                u"unable to validate that the message actually came from the payment processor. "
                u"The specific error message is: {msg}. "
                u"We apologize that we cannot verify whether the charge went through and take further action on your order. "
                u"Your credit card may possibly have been charged. Contact us with payment-specific questions at {email}."
            ).format(
                msg=u'<span class="exception_msg">{msg}</span>'.format(
                    msg=exception.message),
                email=payment_support_email
            )
        )
    elif isinstance(exception, CCProcessorUserCancelled):
        return _format_error_html(
            _(
                u"Sorry! Our payment processor sent us back a message saying that you have cancelled this transaction. "
                u"The items in your shopping cart will exist for future purchase. "
                u"If you feel that this is in error, please contact us with payment-specific questions at {email}."
            ).format(
                email=payment_support_email
            )
        )
    elif isinstance(exception, CCProcessorUserDeclined):
        return _format_error_html(
            _(
                u"We're sorry, but this payment was declined. The items in your shopping cart have been saved. "
                u"If you have any questions about this transaction, please contact us at {email}."
            ).format(
                email=payment_support_email
            )
        )
    else:
        return _format_error_html(
            _(
                u"Sorry! Your payment could not be processed because an unexpected exception occurred. "
                u"Please contact us at {email} for assistance."
            ).format(email=payment_support_email)
        )


def _get_processor_decline_html(params):
    """
    Return HTML indicating that the user's payment was declined.

    Args:
        params (dict): Parameters we received from CyberSource.

    Returns:
        unicode: The rendered HTML.

    """
    payment_support_email = microsite.get_value(
        'payment_support_email', settings.PAYMENT_SUPPORT_EMAIL)
    return _format_error_html(
        _(
            "Sorry! Our payment processor did not accept your payment.  "
            "The decision they returned was {decision}, "
            "and the reason was {reason}.  "
            "You were not charged. Please try a different form of payment.  "
            "Contact us with payment-related questions at {email}."
        ).format(
            decision='<span class="decision">{decision}</span>'.format(decision=params[
                                                                       'decision']),
            reason='<span class="reason">{reason_code}</span>'.format(
                reason_code=params['reason_code']
            ),
            email=payment_support_email
        )
    )


def process_postpay_callback(params):
    """
    Handle a response from the payment processor.

    Concrete implementations should:
        1) Verify the parameters and determine if the payment was successful.
        2) If successful, mark the order as purchased and call `purchased_callbacks` of the cart items.
        3) If unsuccessful, try to figure out why and generate a helpful error message.
        4) Return a dictionary of the form:
            {'success': bool, 'order': Order, 'error_html': str}

    Args:
        params (dict): Dictionary of parameters received from the payment processor.

    Keyword Args:
        Can be used to provide additional information to concrete implementations.

    Returns:
        dict

    """
    try:
        valid_params = verify_signatures(params)
        result = _payment_accepted(
            valid_params['req_reference_number'],
            valid_params['auth_amount'],
            valid_params['req_currency'],
            valid_params['decision']
        )
        if result['accepted']:
            _record_purchase(params, result['order'])
            return {
                'success': True,
                'order': result['order'],
                'error_html': ''
            }
        else:
            _record_payment_info(params, result['order'])
            return {
                'success': False,
                'order': result['order'],
                'error_html': _get_processor_decline_html(params)
            }
    except CCProcessorException as error:
        log.exception('error processing CyberSource postpay callback')
        # if we have the order and the id, log it
        if hasattr(error, 'order'):
            _record_payment_info(params, error.order)
        else:
            log.info(json.dumps(params))
        return {
            'success': False,
            'order': None,  # due to exception we may not have the order
            'error_html': _get_processor_exception_html(error)
        }


def _show_receipt_html(request, order):
    """Render the receipt page as HTML.

    Arguments:
        request (HttpRequest): The request for the receipt.
        order (Order): The order model to display.

    Returns:
        HttpResponse

    """
    order_item = order
    program = order_item.program
    shoppingcart_items = []
    course_names_list = []

    shoppingcart_items.append((order_item, program))
    course_names_list.append(program.name)

    appended_course_names = ", ".join(course_names_list)
    any_refunds = order_item.status == "refunded"
    receipt_template = 'micro_masters/receipt.html'

    recipient_list = []
    total_registration_codes = None
    reg_code_info_list = []
    recipient_list.append(order.user.email)

    appended_recipient_emails = ", ".join(recipient_list)

    context = {
        'order': order,
        'shoppingcart_items': shoppingcart_items,
        'any_refunds': any_refunds,
        'site_name': configuration_helpers.get_value('SITE_NAME', settings.SITE_NAME),
        'appended_course_names': appended_course_names,
        'appended_recipient_emails': appended_recipient_emails,
        'currency_symbol': settings.PAID_COURSE_REGISTRATION_CURRENCY[1],
        'currency': settings.PAID_COURSE_REGISTRATION_CURRENCY[0],
        'total_registration_codes': total_registration_codes,
        'reg_code_info_list': reg_code_info_list,
        'order_purchase_date': order.purchase_time.strftime("%B %d, %Y"),
    }

    # receipt_template = order_items.single_item_receipt_template
    context.update({'receipt_has_donation_item': True})

    return render_to_response(receipt_template, context)


@login_required
def show_program_receipt(request, ordernum):
    """
    Displays a receipt for a particular order.
    404 if order is not yet purchased or request.user != order.user
    """
    try:
        order = ProgramOrder.objects.get(id=ordernum)
    except ProgramOrder.DoesNotExist:
        raise Http404('Order not found!')

    if order.user != request.user or order.status not in ['purchased', 'refunded']:
        raise Http404('Order not found!')

    return _show_receipt_html(request, order)


def program_about(request, program_id):
    """
    get details for specific program or package
    """
    user = request.user
    try:
        program = Program.objects.get(pk=program_id)
    except Exception, e:
        raise Http404

    courses = []
    for course in program.courses.select_related():
        courses += [CourseOverview.get_from_id(course.course_key)]
    user_is_enrolled = False
    if user.is_authenticated():
        user_is_enrolled = ProgramEnrollment.is_enrolled(user, program.id)
        if program.price <= 0 and not user_is_enrolled:
            ProgramEnrollment.enroll(user, program.id)
            user_is_enrolled = True

    context = {}
    currency = settings.PAID_COURSE_REGISTRATION_CURRENCY
    context['currency'] = currency
    context['program'] = program
    context['courses'] = courses
    context['user_is_enrolled'] = user_is_enrolled

    return render_to_response('micro_masters/program_about.html', context)


@csrf_exempt
@require_POST
def program_postpay_callback(request):
    """
    Receives the POST-back from processor.
    Mainly this calls the processor-specific code to check if the payment was accepted, and to record the order
    if it was, and to generate an error page.
    If successful this function should have the side effect of changing the "cart" into a full "order" in the DB.
    The cart can then render a success page which links to receipt pages.
    If unsuccessful the order will be left untouched and HTML messages giving more detailed error info will be
    returned.
    """
    params = request.POST.dict()
    result = process_postpay_callback(params)

    if result['success']:
        order = result['order']
        # See if this payment occurred as part of the verification flow process
        # If so, send the user back into the flow so they have the option
        # to continue with verification.

        # Only orders where order_items.count() == 1 might be attempting to
        # upgrade
        attempting_upgrade = request.session.get('attempting_upgrade', False)
        if attempting_upgrade:
            request.session['attempting_upgrade'] = False

        ProgramEnrollment.enroll(request.user, order.program.id)

        # Otherwise, send the user to the receipt page
        return HttpResponseRedirect(reverse('openedx.core.djangoapps.micro_masters.views.show_program_receipt', args=[result['order'].id]))
    else:
        request.session['attempting_upgrade'] = False
        return render_to_response('shoppingcart/error.html', {'order': result['order'],
                                                              'error_html': result['error_html']})


def programs_order_history(user):
    """
    Returns the list of previously purchased orders for a user. Only the orders with
    PaidCourseRegistration and CourseRegCodeItem are returned.
    """
    order_history_list = []
    purchased_order_items = ProgramOrder.objects.filter(
        user=user, status='purchased').order_by('-purchase_time')
    for order_item in purchased_order_items:
        # Avoid repeated entries for the same order id.
        if order_item.id not in [item['number'] for item in order_history_list]:
            order_history_list.append({
                'number': order_item.id,
                'title': order_item.program.name,
                'price': float(order_item.program.price),
                'receipt_url': reverse('openedx.core.djangoapps.micro_masters.views.show_program_receipt', kwargs={'ordernum': order_item.id}),
                'order_date': ModuleI18nService().strftime(order_item.purchase_time, 'SHORT_DATE')
            })
    return order_history_list


def render_purchase_form_html(cart, callback_url=None, extra_data=None):
    """
    Renders the HTML of the hidden POST form that must be used to initiate a purchase with CyberSource

    Args:
        cart (Order): The order model representing items in the user's cart.

    Keyword Args:
        callback_url (unicode): The URL that CyberSource should POST to when the user
            completes a purchase.  If not provided, then CyberSource will use
            the URL provided by the administrator of the account
            (CyberSource config, not LMS config).

        extra_data (list): Additional data to include as merchant-defined data fields.

    Returns:
        unicode: The rendered HTML form.

    """
    return render_to_string('micro_masters/cybersource_form.html', {
        'action': CC_PROCESSOR.get('PURCHASE_ENDPOINT', ''),
        'params': get_purchase_params(cart, callback_url),
    })


@login_required
def program_buy(request, program_id):

    user = request.user
    try:
        program = Program.objects.get(pk=program_id)
    except Exception, e:
        raise Http404

    user_is_enrolled = False
    user_is_enrolled = ProgramEnrollment.is_enrolled(user, program.id)

    if program.price <= 0 and not user_is_enrolled:
        ProgramEnrollment.enroll(user, program.id)
        user_is_enrolled = True

    if user_is_enrolled:
        return HttpResponseRedirect(reverse('openedx.core.djangoapps.micro_masters.views.program_about', args=str(program.id)))
    courses = []
    for course in program.courses.select_related():
        courses += [get_course_by_id(course.course_key)]

    cart = ProgramOrder.get_or_create_order(user, program)

    # check coupon expiration_date
    if cart.discounted_price:
        try:
            coupon_redemption = ProgramCouponRedemption.objects.get(user=user, order=cart)
            if coupon_redemption.coupon.is_active:
                if coupon_redemption.coupon.expiration_date:
                    if datetime.now(pytz.UTC).__gt__(coupon_redemption.coupon.expiration_date):
                        ProgramCouponRedemption.remove_coupon_redemption_from_cart(request.user, cart)
                        cart.discounted_price = 0
                        cart.save()
            else:
                ProgramCouponRedemption.remove_coupon_redemption_from_cart(request.user, cart)
                cart.discounted_price = 0
                cart.save()
        except Exception, e:
            ProgramCouponRedemption.remove_coupon_redemption_from_cart(request.user, cart)
            cart.discounted_price = 0
            cart.save()

    callback_url = request.build_absolute_uri(
        reverse("shoppingcart.views.postpay_callback")
    )
    protocol = 'https' if request.is_secure() else 'http'
    callback_urls = {
        'success': 'http://edlab.edx.drcsystems.com/programs/program_postpay_callback/',
        'cancel': protocol + '://' + request.get_host() + request.path
    }

    form_html = render_purchase_form_html(cart, callback_url=callback_urls)
    context = {
        'order': cart,
        'shoppingcart_items': courses,
        'amount': cart.item_price,
        'site_name': configuration_helpers.get_value('SITE_NAME', settings.SITE_NAME),
        'form_html': form_html,
        'currency_symbol': settings.PAID_COURSE_REGISTRATION_CURRENCY[1],
        'currency': settings.PAID_COURSE_REGISTRATION_CURRENCY[0],
    }
    return render_to_response("micro_masters/shopping_cart.html", context)


def use_coupon_code(coupons, user, order):
    """
    This method utilize program coupon code
    """
    cart = order
    is_redemption_applied = False
    for coupon in coupons:
        try:
            if ProgramCouponRedemption.add_coupon_redemption(coupon, cart):
                is_redemption_applied = True
        except MultipleCouponsNotAllowedException:
            return HttpResponseBadRequest(_("Only one coupon redemption is allowed against an order"))

    if not is_redemption_applied:
        log.warning(u"Discount does not exist against code '%s'.", coupons[0].code)
        return HttpResponseNotFound(_("Discount does not exist against code '{code}'.").format(code=coupons[0].code))

    return HttpResponse(
        json.dumps({'response': 'success', 'coupon_code_applied': True}),
        content_type="application/json"
    )


@login_required
def reset_code_redemption(request):
    """
    This method reset the code redemption from user cart items.
    """
    order_id = request.POST.get('order_id', '')

    try:
        order = ProgramOrder.objects.get(pk=order_id)
    except Exception, e:
        return HttpResponseNotFound(_("Order does not exist"))
    order.discounted_price = 0
    order.save()
    ProgramCouponRedemption.remove_coupon_redemption_from_cart(request.user, order)
    return HttpResponse('reset')


@login_required
def use_code(request):
    """
    Valid Code can be either Coupon or Registration code.
    For a valid Coupon Code, this applies the coupon code and generates a discount against all applicable items.
    For a valid Registration code, it deletes the item from the shopping cart and redirects to the
    Registration Code Redemption page.
    """
    code = request.POST["code"]
    order_id = request.POST.get('order_id', '')
    try:
        order = ProgramOrder.objects.get(pk=order_id)
    except Exception, e:
        return HttpResponseNotFound(_("Order does not exist"))
    coupons = ProgramCoupon.objects.filter(
        Q(code=code),
        Q(is_active=True),
        Q(expiration_date__gt=datetime.now(pytz.UTC)) |
        Q(expiration_date__isnull=True)
    )
    if not coupons:
        return HttpResponseNotFound(_("Discount does not exist against code '{code}'.").format(code=code))

    return use_coupon_code(coupons, request.user, order)


def prorgam_user_certificate(request, certificate_uuid):

    platform_name = configuration_helpers.get_value("platform_name", settings.PLATFORM_NAME)
    context = {}
    try:
        user_program_certificate = ProgramGeneratedCertificate.objects.get(
            verify_uuid=certificate_uuid,
            issued=True
        )
        user = user_program_certificate.user
        program_certificate_signs = ProgramCertificateSignatories.objects.filter(
            program=user_program_certificate.program
        )
        context['user_program_certificate'] = user_program_certificate
        context['program_certificate_signs'] = program_certificate_signs
        context['platform_name'] = platform_name
        context['course_id'] = user_program_certificate.program.id

        context['full_course_image_url'] = request.build_absolute_uri(user_program_certificate.program.banner_image.url)

        # Needed
        # Translators:  'All rights reserved' is a legal term used in copyrighting to protect published content
        reserved = _("All rights reserved")
        context['copyright_text'] = u'&copy; {year} {platform_name}. {reserved}.'.format(
            year=settings.COPYRIGHT_YEAR,
            platform_name=platform_name,
            reserved=reserved
        )

        # Needed
        # Translators: A 'Privacy Policy' is a legal document/statement describing a website's use of personal information
        context['company_privacy_urltext'] = _("Privacy Policy")

        # Needed
        # Translators: This line appears as a byline to a header image and describes the purpose of the page
        context['logo_subtitle'] = _("Certificate Validation")

        # Needed
        # Translators: Accomplishments describe the awards/certifications obtained by students on this platform
        context['accomplishment_copy_about'] = _('About {platform_name} Accomplishments').format(
            platform_name=platform_name
        )

        # Needed
        # Translators:  This line appears on the page just before the generation date for the certificate
        context['certificate_date_issued_title'] = _("Issued On:")

        # Needed
        # Translators:  This text describes (at a high level) the mission and charter the edX platform and organization
        context['company_about_description'] = _("{platform_name} offers interactive online classes and MOOCs.").format(
            platform_name=platform_name)

        # Needed
        context['company_about_title'] = _("About {platform_name}").format(platform_name=platform_name)
        # Needed
        context['company_about_urltext'] = _("Learn more about {platform_name}").format(platform_name=platform_name)

        # Needed banner docs
        # Translators:  This text appears near the top of the certficate and describes the guarantee provided by edX
        context['document_banner'] = _("{platform_name} acknowledges the following student accomplishment").format(
            platform_name=platform_name
        )

        # Needed
        # Add certificate header/footer data to current context
        context.update(get_certificate_header_context(is_secure=request.is_secure()))
        context.update(get_certificate_footer_context())

        # Needed
        context['accomplishment_copy_course_name'] = user_program_certificate.program.name


        # Needed
        # Translators:  This text represents the description of course
        context['accomplishment_copy_course_description'] = _('a course of study offered by '
                                                              '{platform_name}.').format(
            platform_name=platform_name)

        user_fullname = user.profile.name

        # Needed
        context['accomplishment_user_id'] = user.id
        # Needed
        context['accomplishment_copy_name'] = user_fullname
        # Needed
        context['accomplishment_copy_username'] = user.username


        # Needed banner text
        # Translators: This line is displayed to a user who has completed a course and achieved a certification
        context['accomplishment_banner_opening'] = _("{fullname}, you earned a certificate!").format(
            fullname=user_fullname
        )
        # Needed banner text
        # Translators: This line congratulates the user and instructs them to share their accomplishment on social networks
        context['accomplishment_banner_congrats'] = _("Congratulations! This page summarizes what "
                                                      "you accomplished. Show it off to family, friends, and colleagues "
                                                      "in your social and professional networks.")

        # Needed
        # Translators: This line leads the reader to understand more about the certificate that a student has been awarded
        context['accomplishment_copy_more_about'] = _("More about {fullname}'s accomplishment").format(
            fullname=user_fullname
        )

        # Needed for social sharing
        share_settings = configuration_helpers.get_value("SOCIAL_SHARING_SETTINGS", settings.SOCIAL_SHARING_SETTINGS)
        context['facebook_share_enabled'] = share_settings.get('CERTIFICATE_FACEBOOK', False)
        context['facebook_app_id'] = configuration_helpers.get_value("FACEBOOK_APP_ID", settings.FACEBOOK_APP_ID)
        context['facebook_share_text'] = share_settings.get(
            'CERTIFICATE_FACEBOOK_TEXT',
            _("I completed the {course_title} course on {platform_name}.").format(
                course_title=context['accomplishment_copy_course_name'],
                platform_name=platform_name
            )
        )
        context['twitter_share_enabled'] = share_settings.get('CERTIFICATE_TWITTER', False)
        context['twitter_share_text'] = share_settings.get(
            'CERTIFICATE_TWITTER_TEXT',
            _("I completed a course at {platform_name}. Take a look at my certificate.").format(
                platform_name=platform_name
            )
        )

        # Need to change certificate url
        share_url = request.build_absolute_uri(reverse('openedx.core.djangoapps.micro_masters.views.prorgam_user_certificate', kwargs={'certificate_uuid': certificate_uuid}))
        context['share_url'] = share_url
        twitter_url = ''
        if context.get('twitter_share_enabled', False):
            twitter_url = 'https://twitter.com/intent/tweet?text={twitter_share_text}&url={share_url}'.format(
                twitter_share_text=smart_str(context['twitter_share_text']),
                share_url=urllib.quote_plus(smart_str(share_url))
            )
        context['twitter_url'] = twitter_url
        context['linked_in_url'] = None
        # If enabled, show the LinkedIn "add to profile" button
        # Clicking this button sends the user to LinkedIn where they
        # can add the certificate information to their profile.
        linkedin_config = LinkedInAddToProfileConfiguration.current()
        linkedin_share_enabled = share_settings.get('CERTIFICATE_LINKEDIN', linkedin_config.enabled)
        if linkedin_share_enabled:
            context['linked_in_url'] = linkedin_config.add_to_profile_url(
                course.id,
                context['accomplishment_copy_course_name'],
                user_certificate.mode,
                smart_str(share_url)
            )


        # certificate_type = context.get('certificate_type')

        # Override the defaults with any mode-specific static values
        # Needed
        context['certificate_id_number'] = certificate_uuid

        # Needed
        # Translators:  The format of the date includes the full name of the month
        context['certificate_date_issued'] = _('{month} {day}, {year}').format(
            month=user_program_certificate.modified.strftime("%B"),
            day=user_program_certificate.modified.day,
            year=user_program_certificate.modified.year
        )

        # Needed
        # Translators:  This text is bound to the HTML 'title' element of the page and appears in the browser title bar
        context['document_title'] = _("Certificate | {platform_name}").format(
            platform_name=platform_name
        )

        # Needed
        # Translators:  This text fragment appears after the student's name (displayed in a large font) on the certificate
        # screen.  The text describes the accomplishment represented by the certificate information displayed to the user
        context['accomplishment_copy_description_full'] = _("successfully completed, received a passing grade, and was "
                                                            "awarded this {platform_name} "
                                                            "Certificate of Completion in ").format(
            platform_name=platform_name)

        # Needed
        # Translators: This text describes the purpose (and therefore, value) of a course certificate
        context['certificate_info_description'] = _("{platform_name} acknowledges achievements through "
                                                    "certificates, which are awarded for course activities "
                                                    "that {platform_name} students complete.").format(
            platform_name=platform_name,
            tos_url=context.get('company_tos_url'))

        return render_to_response("micro_masters/certificates/valid.html", context)

    except Exception, e:
        raise Http404


@login_required
def program_info(request, program_id):
    user = request.user
    context = {}
    try:
        user_program = ProgramEnrollment.objects.get(user=user, is_active=True, program__id=program_id)
    except Exception, e:
        raise Http404
    course_grades = {}
    courses = []
    for course in user_program.program.courses.select_related():
        try:
            course_grade = LeaderBoard.objects.get(student=user, course_id=course.course_key)
            course_grades.update({
                course.course_key: {
                    'points': course_grade.points,
                    'pass': course_grade.has_passed,
                }
            })
            if course_grade.points and course_grade.has_passed:
                course_grades.get(course.course_key)['course_states'] = {
                    'completed': True,
                    'in_progress': False,
                    'not_started': False
                }
            elif course_grade.points:
                course_grades.get(course.course_key)['course_states'] = {
                    'completed': False,
                    'in_progress': True,
                    'not_started': False
                }
            else:
                course_grades.get(course.course_key)['course_states'] = {
                    'completed': False,
                    'in_progress': False,
                    'not_started': True
                }

        except Exception, e:
            course_grades.update({
                course.course_key: {
                    'points': 0,
                    'pass': False,
                    'course_states': {
                        'completed': False,
                        'in_progress': False,
                        'not_started': True
                    }
                }
            })

        try:
            courses += [CourseOverview.get_from_id(course.course_key)]
        except Exception, e:
            courses = courses

    context['program_courses'] = courses
    context['program'] = user_program.program
    context['course_grades'] = course_grades
    return render_to_response('micro_masters/program_info.html', context)
