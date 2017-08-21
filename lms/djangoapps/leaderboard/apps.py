"""
Leaderboard Application Configuration

Signal handlers are connected here.
"""

from django.apps import AppConfig


class LeaderboardConfig(AppConfig):
    """
    Application Configuration for Leaderboard.
    """
    name = u'leaderboard'

    def ready(self):
        """
        Connect handlers to recalculate ranks.
        """
        # Can't import models at module level in AppConfigs, and models get
        # included from the signal handlers
        from .signals import handlers  # pylint: disable=unused-variable
