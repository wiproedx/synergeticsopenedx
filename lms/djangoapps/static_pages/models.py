from mongoengine import *
connect('edxapp')

class StaticPage(Document):
    about = StringField(required=False)
    faq = StringField(required=False)
    privacy =StringField(required=False)
    honor = StringField(required=False)
    tos = StringField(required=False)
    contact = StringField(required=False)
    blog = StringField(required=False)

    @classmethod
    def get_content(cls):
        if len(cls.objects.all()) != 0:
            content = cls.objects.all()[0]
        else:
            content = cls.objects.create()
        return content

    @classmethod
    def update_content(cls, page, content):
        try:
            obj = cls.objects.all()[0]
            setattr(obj, page, content)
            obj.save()
            return {
                'success': True,
                'error_msg': ''
            }
        except Exception as error:
            return {
                'success': False,
                'error_msg': error.message
            }
