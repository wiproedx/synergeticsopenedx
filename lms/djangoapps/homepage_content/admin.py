from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import Testimonials, StatisticalCounter


class TestimonialsAdmin(admin.ModelAdmin):
    list_display = ['name', 'image_tag', 'is_active', 'quotes']
    list_filter = ['is_active']
    search_fields = ['name']

    class Meta:
        verbose_name = "Testimonial"
        verbose_name_plural = "Testimonials"


admin.site.register(StatisticalCounter, SingletonModelAdmin)
admin.site.register(Testimonials, TestimonialsAdmin)
