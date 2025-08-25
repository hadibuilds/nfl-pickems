"""
Slimmed snapshot command: freeze ONLY leaderboard + per-user RankHistory.
No more heavy WeeklySnapshot writes; use realtime logic to compute ranks as of the specified (completed) week.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from predictions.models import RankHistory, LeaderboardSnapshot
from games.models import Game

User = get_user_model()

class Command(BaseCommand):
    help = 'Freeze weekly leaderboard + rank deltas (audit only)'

    def add_arguments(self, parser):
        parser.add_argument('--week', type=int, help='Completed NFL week to freeze. Default: latest completed week')
        parser.add_argument('--force', action='store_true', help='Overwrite existing snapshot for the week')

    def handle(self, *args, **opts):
        week = opts.get('week') or self._latest_completed_week()
        if not week:
            self.stdout.write(self.style.WARNING('No completed weeks found'))
            return

        if LeaderboardSnapshot.objects.filter(week=week).exists() and not opts.get('force'):
            self.stdout.write(self.style.WARNING(f'Week {week} snapshot already exists. Use --force to overwrite.'))
            return

        # compute totals THROUGH this week from raw data
        standings = self._compute_totals_through_week(week)

        # write LeaderboardSnapshot (compact)
        leaderboard_data = [
            {'rank': i+1, 'username': u.username, 'points': pts}
            for i, (u, pts) in enumerate(standings)
        ]
        LeaderboardSnapshot.objects.update_or_create(
            week=week, defaults={'snapshot_data': leaderboard_data}
        )

        # write RankHistory (rank, previous_rank, rank_change, total_points)
        for i, (user, points) in enumerate(standings):
            rank = i + 1
            prev = RankHistory.objects.filter(user=user, week__lt=week).order_by('-week').first()
            prev_rank = prev.rank if prev else None
            change = (prev_rank - rank) if prev_rank else 0
            RankHistory.objects.update_or_create(
                user=user, week=week,
                defaults={'rank': rank, 'previous_rank': prev_rank, 'rank_change': change, 'total_points': points}
            )

        self.stdout.write(self.style.SUCCESS(f'Frozen leaderboard + rank history for Week {week}'))

    # ---------- helpers ----------
    def _latest_completed_week(self):
        weeks = list(Game.objects.values_list('week', flat=True).distinct())
        for wk in sorted(weeks, reverse=True):
            q = Game.objects.filter(week=wk)
            if q.exists() and q.filter(winner__isnull=False).count() == q.count():
                return wk
        return None

    def _compute_totals_through_week(self, through_week):
        # Compute each user’s total points through 'through_week' inclusive, from raw predictions.
        # Moneyline = 1, Prop = 2
        results = []
        for u in User.objects.all():
            # moneyline
            ml_correct = u.prediction_set.filter(game__week__lte=through_week, game__winner__isnull=False, is_correct=True).count()
            # props
            pb_correct = u.propbetprediction_set.filter(prop_bet__game__week__lte=through_week, is_correct=True).count()
            total = ml_correct + (pb_correct * 2)
            results.append((u, total))
        results.sort(key=lambda t: (-t[1], t[0].username))
        return results