from django.conf.urls import url
from .views import (
    program_about, program_postpay_callback,
    show_program_receipt, program_buy,
    use_code, reset_code_redemption,
    prorgam_user_certificate,
    program_info
)
from .program_reindex import index_programs_information

urlpatterns = [
    url(r'^(?P<program_id>[0-9]+)/$', program_about, name='program_about'),
    url(r'^(?P<program_id>[0-9]+)/info$', program_info, name='program_info'),
    url(r'^receipt/(?P<ordernum>[0-9]+)/$', show_program_receipt),
    url(r'^buy/(?P<program_id>[0-9]+)/$', program_buy, name='program_buy'),
    # response from payment gateway for programs
    url(r'^program_postpay_callback/$', program_postpay_callback),  # Both the ~accept and ~reject callback pages are handled here
    url(r'^use_code/$', use_code),
    url(r'^reset_code_redemption/$', reset_code_redemption),

    # for reindex all programs
    url(r'^reindex_programs/$', index_programs_information),

    # user program certificate
    url(
        r'^certificates/(?P<certificate_uuid>[0-9a-f]{32})/$',
        prorgam_user_certificate,
        name='prorgam_user_certificate'
    ),
]
