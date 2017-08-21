from django.http import HttpResponseNotFound
from edxmako.shortcuts import render_to_response
from static_pages.models import StaticPage

def add_content(static_page):
    context = {}
    PAGE_TITLE ={
        u'about': 'About',
        u'blog': 'Blog',
        u'contact': 'Contact',
        u'privacy':'Privacy Policy', 
        u'tos':'Terms of Service', 
        u'faq':'FAQ', 
        u'honor': 'Honor Code'
    }
    try:
        content = StaticPage.get_content()
        page_content = getattr(content, static_page)
    except:
        return HttpResponseNotFound("Page Not Found")

    context['title'] = PAGE_TITLE[static_page]
    if page_content is None:
        context['content'] = "<p>This page is intentionally left blank. Feel Free to add your content.</p>"
    else:
        context['content'] = page_content
    return render_to_response('static_pages/common_static_content.html', context)
