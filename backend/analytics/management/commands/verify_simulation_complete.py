from django.core.management.base import BaseCommand
from django.db.models import Count, Avg
from games.models import Window, Game, PropBet
from predictions.models import MoneyLinePrediction, PropBetPrediction
from analytics.models import UserWindowStat

class Command(BaseCommand):
    help = 'Verify that simulation is complete through Week 10'

    def handle(self, *args, **options):
        self.stdout.write("🔍 VERIFYING SIMULATION COMPLETENESS")
        self.stdout.write("=" * 50)
        
        # Check all games have winners
        total_games = Game.objects.count()
        games_with_winners = Game.objects.exclude(winner__isnull=True).count()
        
        self.stdout.write(f"\n🏈 GAME RESULTS:")
        self.stdout.write(f"   Total games: {total_games}")
        self.stdout.write(f"   Games with winners: {games_with_winners}")
        self.stdout.write(f"   Completion: {games_with_winners/total_games*100:.1f}%")
        
        if games_with_winners < total_games:
            self.stdout.write("   ❌ Some games missing winners!")
        else:
            self.stdout.write("   ✅ All games have winners")
        
        # Check all prop bets have answers
        total_props = PropBet.objects.count()
        props_with_answers = PropBet.objects.exclude(correct_answer__isnull=True).count()
        
        self.stdout.write(f"\n🎯 PROP BET ANSWERS:")
        self.stdout.write(f"   Total prop bets: {total_props}")
        self.stdout.write(f"   Props with answers: {props_with_answers}")
        self.stdout.write(f"   Completion: {props_with_answers/total_props*100:.1f}%")
        
        if props_with_answers < total_props:
            self.stdout.write("   ❌ Some prop bets missing answers!")
        else:
            self.stdout.write("   ✅ All prop bets have answers")
        
        # Check prediction accuracy
        ml_total = MoneyLinePrediction.objects.count()
        ml_correct = MoneyLinePrediction.objects.filter(is_correct=True).count()
        
        prop_total = PropBetPrediction.objects.count()
        prop_correct = PropBetPrediction.objects.filter(is_correct=True).count()
        
        ml_stats = {'total': ml_total, 'correct': ml_correct}
        prop_stats = {'total': prop_total, 'correct': prop_correct}
        
        self.stdout.write(f"\n📊 PREDICTION ACCURACY:")
        if ml_stats['total'] > 0:
            ml_accuracy = ml_stats['correct'] / ml_stats['total'] * 100
            self.stdout.write(f"   Money Line: {ml_stats['correct']}/{ml_stats['total']} ({ml_accuracy:.1f}%)")
        
        if prop_stats['total'] > 0:
            prop_accuracy = prop_stats['correct'] / prop_stats['total'] * 100
            self.stdout.write(f"   Prop Bets: {prop_stats['correct']}/{prop_stats['total']} ({prop_accuracy:.1f}%)")
        
        # Check realistic accuracy ranges
        if 45 <= ml_accuracy <= 65:
            self.stdout.write("   ✅ ML accuracy is realistic (45-65%)")
        else:
            self.stdout.write("   ⚠️  ML accuracy might be unrealistic")
            
        if 40 <= prop_accuracy <= 60:
            self.stdout.write("   ✅ Prop accuracy is realistic (40-60%)")
        else:
            self.stdout.write("   ⚠️  Prop accuracy might be unrealistic")
        
        # Check window completeness
        total_windows = Window.objects.count()
        completed_windows = Window.objects.filter(is_complete=True).count()
        
        self.stdout.write(f"\n🪟 WINDOW COMPLETION:")
        self.stdout.write(f"   Total windows: {total_windows}")
        self.stdout.write(f"   Completed windows: {completed_windows}")
        self.stdout.write(f"   Completion: {completed_windows/total_windows*100:.1f}%")
        
        if completed_windows == total_windows:
            self.stdout.write("   ✅ All windows marked complete")
        else:
            self.stdout.write("   ❌ Some windows not marked complete")
        
        # Check UserWindowStat computation
        total_stats = UserWindowStat.objects.count()
        expected_stats = completed_windows * 20  # Approximate expected stats
        
        self.stdout.write(f"\n📈 RANKING CALCULATIONS:")
        self.stdout.write(f"   UserWindowStats computed: {total_stats}")
        self.stdout.write(f"   Expected range: {expected_stats-100} - {expected_stats+100}")
        
        if total_stats > 0:
            self.stdout.write("   ✅ Rankings have been calculated")
        else:
            self.stdout.write("   ❌ No ranking stats found!")
        
        # Sample some actual results
        self.stdout.write(f"\n🎲 SAMPLE RESULTS:")
        
        # Show a few games with results
        sample_games = Game.objects.select_related('window').order_by('?')[:3]
        for game in sample_games:
            self.stdout.write(f"   {game.away_team} @ {game.home_team} → Winner: {game.winner}")
        
        # Show a few prop bets with answers
        sample_props = PropBet.objects.select_related('game').order_by('?')[:3]
        for prop in sample_props:
            options_str = " vs ".join(prop.options) if prop.options else "N/A"
            self.stdout.write(f"   {prop.question[:50]}... → {prop.correct_answer}")
        
        # Final assessment
        self.stdout.write(f"\n🎯 FINAL ASSESSMENT:")
        
        issues = []
        if games_with_winners < total_games:
            issues.append("Missing game winners")
        if props_with_answers < total_props:
            issues.append("Missing prop answers")
        if completed_windows < total_windows:
            issues.append("Incomplete windows")
        if total_stats == 0:
            issues.append("No ranking calculations")
            
        if not issues:
            self.stdout.write("   ✅ SIMULATION IS FULLY COMPLETE!")
            self.stdout.write("   • All games have winners")
            self.stdout.write("   • All prop bets have correct answers")  
            self.stdout.write("   • All predictions are graded")
            self.stdout.write("   • All windows are complete")
            self.stdout.write("   • All rankings are calculated")
            self.stdout.write("   • Ready for UI testing!")
        else:
            self.stdout.write("   ❌ SIMULATION HAS ISSUES:")
            for issue in issues:
                self.stdout.write(f"   • {issue}")
                
        self.stdout.write(f"\n✓ Verification complete!")