from django import forms

from .models import (
    Program, Subject,
    ProgramCoupon, Language,
    ProgramEnrollment, Institution,
    Instructor, ProgramEnrollment,
    ProgramCertificateSignatories
)


class ProgramForm(forms.ModelForm):

    class Meta:
        model = Program
        widgets = {
            'start': forms.DateInput(attrs={'class': 'datepicker'}),
            'end': forms.DateInput(attrs={'class': 'datepicker'}),
        }
        fields = [
            'name',
            'start',
            'end',
            'short_description',
            'price',
            'banner_image',
            'introductory_video',
            'overview',
            'sample_certificate_pdf',
            'average_length',
            'effort',
            'language',
            'video_transcripts',
            'subject',
            'institution',
            'instructors',
            'courses',
        ]


class SubjectForm(forms.ModelForm):

    class Meta:
        model = Subject
        fields = [
            'name',
            'mark_as_popular'
        ]


class LanguageForm(forms.ModelForm):

    class Meta:
        model = Language
        fields = [
            'name',
            'code'
        ]


class InstitutionForm(forms.ModelForm):

    class Meta:
        model = Institution
        fields = [
            'name',
            'website_url',
            'logo'
        ]


class InstructorForm(forms.ModelForm):

    class Meta:
        model = Instructor
        fields = [
            'name',
            'designation',
            'profile_image',
            'institution'
        ]


class ProgramEnrollmentForm(forms.ModelForm):

    class Meta:
        model = ProgramEnrollment
        fields = [
            'user',
            'program',
            'is_active'
        ]


class ProgramCertificateSignatoriesForm(forms.ModelForm):

    class Meta:
        model = ProgramCertificateSignatories
        fields = [
            'program',
            'name',
            'title',
            'institution',
            'signature_image',
        ]
