from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from games.models import Window, Game, PropBet
from analytics.services.window_stats_optimized import recompute_window_optimized


class Command(BaseCommand):
    help = 'Ensure all windows with completed games/props are marked as complete'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season', 
            type=int, 
            help='Season to check (defaults to all)'
        )
        parser.add_argument(
            '--fix', 
            action='store_true', 
            help='Actually fix the windows (otherwise just report)'
        )

    def handle(self, *args, **options):
        season = options.get('season')
        fix_mode = options.get('fix', False)
        
        User = get_user_model()
        admin_user = User.objects.first()  # Need an actor for recompute
        
        self.stdout.write(f"🔍 Checking window completion status...")
        if season:
            self.stdout.write(f"   Season: {season}")
            windows = Window.objects.filter(season=season)
        else:
            self.stdout.write("   All seasons")
            windows = Window.objects.all()

        issues_found = 0
        issues_fixed = 0
        
        for window in windows:
            games = Game.objects.filter(window=window)
            if not games.exists():
                continue
                
            games_without_winners = games.filter(winner__isnull=True).count()
            props_without_answers = PropBet.objects.filter(
                game__in=games, 
                correct_answer__isnull=True
            ).count()
            
            should_be_complete = (games_without_winners == 0 and props_without_answers == 0)
            
            if should_be_complete and not window.is_complete:
                issues_found += 1
                self.stdout.write(
                    f"❌ Window {window.id} ({window.date} {window.slot}) should be complete but isn't"
                )
                
                if fix_mode:
                    try:
                        recompute_window_optimized(window.id, actor=admin_user)
                        window.refresh_from_db()
                        if window.is_complete:
                            issues_fixed += 1
                            self.stdout.write(f"   ✅ Fixed!")
                        else:
                            self.stdout.write(f"   ❌ Still not complete after recompute")
                    except Exception as e:
                        self.stdout.write(f"   ❌ Error fixing: {e}")
        
        if issues_found == 0:
            self.stdout.write("✅ All windows have correct completion status")
        else:
            self.stdout.write(f"\n📊 Summary:")
            self.stdout.write(f"   Issues found: {issues_found}")
            if fix_mode:
                self.stdout.write(f"   Issues fixed: {issues_fixed}")
                self.stdout.write(f"   Issues remaining: {issues_found - issues_fixed}")
            else:
                self.stdout.write("   Run with --fix to fix these issues")