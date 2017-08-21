from django.conf.urls import patterns, url

urlpatterns = patterns(
    'admin_dash.views',

    url(r'^$', 'show_dashboard', name='show_dashboard'),
    url(r'^update-traffic-report/$', 'update_traffic_report', name='update_traffic_report'),
    url(r'^demographics/', 'demographics', name='demographics'),
    url(r'^courses-chart/', 'courses_chart', name='courses-chart'),
    url(r'^revenue-report/', 'revenue_report', name='revenue-report'),
    url(r'^site-content/$', 'site_content', name='site-content'),
    url(r'^add_static_content/$', 'add_static_content', name='add_static_content'),
    url(r'^student-details/$', 'student_details', name='student-details'),
    url(r'^update-user/$', 'update_user', name='update-user'),
    url(r'^update-user/(?P<user>[\w.@+-]+)/$', 'update_user', name='update-user'),
    url(r'^create-user/$', 'create_user', name='create-user'),
    url(r'^delete-user/$', 'delete_user', name='delete-user'),
    url(r'^display-courses/', 'view_courses', name='display-courses'),
    url(r'^update-course-price/', 'update_course_price', name='update-course-price'),
    url(r'^delete-course/', 'delete_course', name='delete-course'),
    url(r'^view-offers/', 'view_coupons', name='view-offers'),
    url(r'^new-coupon/', 'new_coupon', name='new-coupon'),
    url(r'^update-coupon/$', 'update_coupon', name='update-coupon'),
    url(r'^update-coupon/(?P<coupon_id>[\w.@+-]+)/$', 'update_coupon', name='update-coupon'),
    url(r'^delete-coupon/', 'delete_coupon', name='delete-coupon'),
    url(r'^program-offers/', 'program_coupons', name='program-offers'),
    url(r'^new-program-coupon/', 'new_program_coupon', name='new-program-coupon'),
    url(r'^update-program-coupon/$', 'update_program_coupon', name='update-program-coupon'),
    url(r'^update-program-coupon/(?P<coupon_id>[\w.@+-]+)/$', 'update_program_coupon', name='update-program-coupon'),
    url(r'^delete-program-coupon/', 'delete_program_coupon', name='delete-program-coupon'),

    url(r'^program/$', 'show_programs', name='show-programs'),
    url(r'^program/new/$', 'create_program', name='create-program'),
    url(r'^program/edit/(?P<pk>\d+)/$', 'update_program', name='update-program'),
    url(r'^program/delete/(?P<pk>\d+)/$', 'program_delete', name='program-delete'),

    url(r'^subject/$', 'show_subject', name='show-subjects'),
    url(r'^subject/new/$', 'add_subject', name='add-subject'),
    url(r'^subject/edit/(?P<pk>\d+)/$', 'update_subject', name='update-subject'),
    url(r'^subject/delete/(?P<pk>\d+)/$', 'delete_subject', name='delete-subject'),

    url(r'^language/$', 'show_language', name='show-language'),
    url(r'^language/new/$', 'add_language', name='add-language'),
    url(r'^language/edit/(?P<pk>\d+)/$', 'update_language', name='update-language'),
    url(r'^language/delete/(?P<pk>\d+)/$', 'delete_language', name='delete-language'),

    url(r'^instructor/$', 'show_instructor', name='show-instructor'),
    url(r'^instructor/new/$', 'add_instructor', name='add-instructor'),
    url(r'^instructor/edit/(?P<pk>\d+)/$', 'update_instructor', name='update-instructor'),
    url(r'^instructor/delete/(?P<pk>\d+)/$', 'delete_instructor', name='delete-instructor'),

    url(r'^institution/$', 'show_institution', name='show-institution'),
    url(r'^institution/new/$', 'add_institution', name='add-institution'),
    url(r'^institution/edit/(?P<pk>\d+)/$', 'update_institution', name='update-institution'),
    url(r'^institution/delete/(?P<pk>\d+)/$', 'delete_institution', name='delete-institution'),

    url(r'^program-certificate-signatories/$', 'show_signatories', name='show-signatories'),
    url(r'^program-certificate-signatories/new/$', 'add_signatories', name='add-signatories'),
    url(r'^program-certificate-signatories/edit/(?P<pk>\d+)/$', 'update_signatories', name='update-signatories'),
    url(r'^program-certificate-signatories/delete/(?P<pk>\d+)/$', 'delete_signatories', name='delete-signatories'),

)
