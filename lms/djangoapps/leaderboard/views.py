from django.db.models import Sum
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from edxmako.shortcuts import render_to_response

from .models import LeaderBoard


@login_required
def show_leaderboard(request):
    points_leaders = []

    leaderboard = LeaderBoard.objects.all() \
        .exclude(points__isnull=True) \
        .exclude(points=0.0) \
        .values('student') \
        .annotate(points=Sum('points')) \
        .order_by('-points')[:10]

    for leader in leaderboard:
        points_leaders.append({
            'user': User.objects.get(pk=leader['student']),
            'points': leader['points']
        })

    return render_to_response('leaderboard/leaderboard.html', {
        "points_leaders": points_leaders
    })
