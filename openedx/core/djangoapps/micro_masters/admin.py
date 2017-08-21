__author__ = 'DRC Systems'

from django.contrib import admin

from .models import (
    Subject, Language,
    Institution, Instructor,
    Program, ProgramEnrollment,
    ProgramCoupon, ProgramCertificateSignatories,
    ProgramGeneratedCertificate,
    ProgramCouponRedemption, ProgramOrder # need to remove
)


class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"

admin.site.register(Subject, SubjectAdmin)


class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']
    search_fields = ['name', 'code']

    class Meta:
        verbose_name = "Language"
        verbose_name_plural = "Language"

admin.site.register(Language, LanguageAdmin)


class InstitutionAdmin(admin.ModelAdmin):

    list_display = ['name', 'image_tag', 'website_url']
    search_fields = ['name', 'website_url']

    class Meta:
        verbose_name = "Institution"
        verbose_name_plural = "Institution"

admin.site.register(Institution, InstitutionAdmin)


class InstructorAdmin(admin.ModelAdmin):
    list_display = ['name', 'designation', 'get_institution', 'image_tag']
    list_filter = ['designation', 'institution__name']
    search_fields = ['name']

    def get_institution(self, obj):
        return obj.institution.name
    get_institution.admin_order_field  = 'institution'  #Allows column order sorting
    get_institution.short_description = 'institution name'  #Renames column head

    class Meta:
        verbose_name = "Instructor"
        verbose_name_plural = "Instructors"

admin.site.register(Instructor, InstructorAdmin)


class ProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'average_length', 'effort', 'image_tag']
    list_filter = ['language__name', 'subject__name', 'institution__name']
    search_fields = ['name']

    class Meta:
        verbose_name = "Program"
        verbose_name_plural = "Programs"

admin.site.register(Program, ProgramAdmin)


class ProgramEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'program', 'is_active']
    list_filter = ['is_active']
    search_fields = ['program__name', 'user__username']

    class Meta:
        verbose_name = "Program Enrollment"
        verbose_name_plural = "Program Enrollment"

admin.site.register(ProgramEnrollment, ProgramEnrollmentAdmin)


class ProgramCouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'program', 'percentage_discount', 'is_active', 'expiration_date']
    list_filter = ['is_active', 'percentage_discount', 'program']
    search_fields = ['program__name', 'code', 'percentage_discount']

    class Meta:
        verbose_name = "Program Coupon"
        verbose_name_plural = "Program Coupons"

admin.site.register(ProgramCoupon, ProgramCouponAdmin)


class ProgramCouponRedemptionAdmin(admin.ModelAdmin):

    class Meta:
        verbose_name = "Program Coupon Redemption"
        verbose_name_plural = "Program Coupon Redemption"

admin.site.register(ProgramCouponRedemption, ProgramCouponRedemptionAdmin)


class ProgramOrderAdmin(admin.ModelAdmin):

    class Meta:
        verbose_name = "Program Order"
        verbose_name_plural = "Program Order"

admin.site.register(ProgramOrder, ProgramOrderAdmin)


class ProgramCertificateSignatoriesAdmin(admin.ModelAdmin):
    list_display = ['name', 'title', 'institution', 'program', 'image_tag']
    list_filter = ['institution__name', 'program__name']
    search_fields = ['name', 'title']

    class Meta:
        verbose_name = "Program Certificate Signatories"
        verbose_name_plural = "Program Certificate Signatories"

admin.site.register(ProgramCertificateSignatories, ProgramCertificateSignatoriesAdmin)


class ProgramGeneratedCertificateAdmin(admin.ModelAdmin):
    list_display = ['user', 'program', 'issued']
    list_filter = ['program', 'user', 'issued']

    class Meta:
        verbose_name = "Program Generated Certificate"
        verbose_name_plural = "Program Generated Certificate"

admin.site.register(ProgramGeneratedCertificate, ProgramGeneratedCertificateAdmin)
