import datetime
from datetime import datetime as datetime_object

from django.db.models import Count

from attendance.models import CampusAttendance, ClassroomAttendance


def get_traffic_report(start_dt_str, end_dt_str):

    start_date = datetime_object.strptime(start_dt_str, '%d-%m-%Y')
    end_date = datetime_object.strptime(end_dt_str, '%d-%m-%Y')

    campus_attendance = CampusAttendance.objects.filter(
        date_visited__range=(start_date, end_date)
    ).values(
        'date_visited'
    ).annotate(
        count=Count('date_visited')
    ).order_by('date_visited')

    classroom_attendance = ClassroomAttendance.objects.filter(
        date_visited__range=(start_date, end_date)
    ).values(
        'date_visited'
    ).annotate(
        count=Count('date_visited')
    ).order_by('date_visited')

    date_list = get_date_in_range(start_date, end_date)
    visitors = count_by_date(date_list, campus_attendance)
    content_viewers = count_by_date(date_list, classroom_attendance)

    return date_list, visitors, content_viewers


def get_date_in_range(date1, date2):
    sorted_date_range = []
    while date1 <= date2:
        sorted_date_range.append(date1.date().strftime("%d-%m-%Y"))
        date1 += datetime.timedelta(days=1)

    return sorted_date_range


def count_by_date(date_list, data_dict):

    date_wise_count = []
    attendance = {}

    for data in data_dict:
        attendance[data['date_visited'].strftime("%d-%m-%Y")] = data['count']

    for day in date_list:
        date_wise_count.append(attendance.get(day, 0))

    return date_wise_count
