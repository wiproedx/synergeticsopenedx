import datetime


def get_last_month():
    last_day_of_prev_month = datetime.date.today().replace(day=1) - \
        datetime.timedelta(days=1)
    end_date = last_day_of_prev_month.strftime("%d-%m-%Y")
    start_date = last_day_of_prev_month.replace(day=1).strftime("%d-%m-%Y")
    return start_date, end_date
