# predictions/migrations/0012_update_for_rank_based_system.py

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('predictions', '0013_userstathistory_delete_rankhistory_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # =========================================================================
        # STEP 1: Delete UserStreak model entirely (remove streak functionality)
        # =========================================================================
        migrations.DeleteModel(
            name='UserStreak',
        ),
        
        # =========================================================================
        # STEP 2: Update SeasonStats model for rank-based achievements
        # =========================================================================
        
        # Rename existing fields for clarity
        migrations.RenameField(
            model_name='seasonstats',
            old_name='highest_rank',
            new_name='best_rank',
        ),
        migrations.RenameField(
            model_name='seasonstats',
            old_name='highest_rank_week', 
            new_name='best_rank_week',
        ),
        migrations.RenameField(
            model_name='seasonstats',
            old_name='weeks_as_leader',
            new_name='weeks_at_rank_1',
        ),
        
        # Remove old field that's not needed (if it exists)
        # migrations.RemoveField(
        #     model_name='seasonstats',
        #     name='most_successful_category',
        # ),
        
        # Add new rank-based achievement fields
        migrations.AddField(
            model_name='seasonstats',
            name='worst_rank',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='seasonstats',
            name='consecutive_weeks_at_1',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='seasonstats',
            name='max_consecutive_weeks_at_1',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='seasonstats',
            name='biggest_rank_climb',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='seasonstats',
            name='biggest_rank_fall',
            field=models.IntegerField(default=0),
        ),
        
        # Add best_category field (don't alter - just add)
        migrations.AddField(
            model_name='seasonstats',
            name='best_category',
            field=models.CharField(
                choices=[
                    ('moneyline', 'Moneyline'), 
                    ('prop', 'Prop Bets'), 
                    ('balanced', 'Balanced')
                ],
                default='balanced',
                max_length=20
            ),
        ),
        
        # =========================================================================
        # STEP 3: Add comprehensive fields to UserStatHistory model
        # =========================================================================
        
        migrations.AddField(
            model_name='userstathistory',
            name='week_points',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='week_moneyline_correct',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='week_moneyline_total',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='week_prop_correct',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='week_prop_total',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='season_moneyline_correct',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='season_moneyline_total',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='season_prop_correct',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='season_prop_total',
            field=models.IntegerField(default=0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='week_accuracy',
            field=models.FloatField(default=0.0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='season_accuracy',
            field=models.FloatField(default=0.0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='moneyline_accuracy',
            field=models.FloatField(default=0.0, editable=False),
        ),
        migrations.AddField(
            model_name='userstathistory',
            name='prop_accuracy',
            field=models.FloatField(default=0.0, editable=False),
        ),
        
        # =========================================================================
        # STEP 4: Update model metadata and constraints
        # =========================================================================
        
        # Update UserStatHistory Meta options
        migrations.AlterModelOptions(
            name='userstathistory',
            options={
                'ordering': ['week', 'rank'],
                'verbose_name': 'User Statistics History',
                'verbose_name_plural': 'User Statistics History',
            },
        ),
        
        # Add indexes for better performance
        migrations.AddIndex(
            model_name='userstathistory',
            index=models.Index(fields=['user', '-week'], name='predictions_userstat_user_week_idx'),
        ),
        migrations.AddIndex(
            model_name='userstathistory',
            index=models.Index(fields=['week', 'rank'], name='predictions_userstat_week_rank_idx'),
        ),
        migrations.AddIndex(
            model_name='userstathistory',
            index=models.Index(fields=['-total_points'], name='predictions_userstat_points_idx'),
        ),
        
        # Add index for SeasonStats lookups
        migrations.AddIndex(
            model_name='seasonstats',
            index=models.Index(fields=['weeks_at_rank_1', '-weeks_in_top_3'], name='predictions_seasonstat_perf_idx'),
        ),
    ]