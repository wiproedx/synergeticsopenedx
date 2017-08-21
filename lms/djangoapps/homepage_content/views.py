import datetime
from ipware.ip import get_real_ip

from .models import CampusAttendance, ClassroomAttendance


def track_attendance(request):

    ip_address = get_real_ip(request)
    if not ip_address:
        ip_address = '-'

    if request.user.is_authenticated():
        if not ClassroomAttendance.objects.filter(user=request.user.id, date_visited=datetime.date.today()).exists():
            visitor = ClassroomAttendance(
                user=request.user.id, date_visited=datetime.date.today())
            visitor.save()

    else:
        if not CampusAttendance.objects.filter(ip=ip_address, date_visited=datetime.date.today()).exists():
            visitor = CampusAttendance(
                ip=ip_address, date_visited=datetime.date.today())
            visitor.save()
