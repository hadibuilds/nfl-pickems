# predictions/migrations/0005_add_historical_tracking.py

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('predictions', '0004_propbet_propbetprediction'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeeklySnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week', models.IntegerField()),
                ('weekly_points', models.IntegerField(default=0)),
                ('weekly_game_correct', models.IntegerField(default=0)),
                ('weekly_game_total', models.IntegerField(default=0)),
                ('weekly_prop_correct', models.IntegerField(default=0)),
                ('weekly_prop_total', models.IntegerField(default=0)),
                ('total_points', models.IntegerField(default=0)),
                ('total_game_correct', models.IntegerField(default=0)),
                ('total_game_total', models.IntegerField(default=0)),
                ('total_prop_correct', models.IntegerField(default=0)),
                ('total_prop_total', models.IntegerField(default=0)),
                ('rank', models.IntegerField()),
                ('total_users', models.IntegerField()),
                ('points_from_leader', models.IntegerField(default=0)),
                ('weekly_accuracy', models.FloatField(blank=True, null=True)),
                ('overall_accuracy', models.FloatField(blank=True, null=True)),
                ('moneyline_accuracy', models.FloatField(blank=True, null=True)),
                ('prop_accuracy', models.FloatField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['week', 'rank'],
            },
        ),
        migrations.CreateModel(
            name='RankHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week', models.IntegerField()),
                ('rank', models.IntegerField()),
                ('previous_rank', models.IntegerField(blank=True, null=True)),
                ('rank_change', models.IntegerField(default=0)),
                ('total_points', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['week', 'rank'],
            },
        ),
        migrations.CreateModel(
            name='UserStreak',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_streak', models.IntegerField(default=0)),
                ('streak_type', models.CharField(choices=[('win', 'Win'), ('loss', 'Loss')], default='win', max_length=10)),
                ('longest_win_streak', models.IntegerField(default=0)),
                ('longest_loss_streak', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='LeaderboardSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week', models.IntegerField()),
                ('snapshot_data', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='SeasonStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('best_week_points', models.IntegerField(default=0)),
                ('best_week_number', models.IntegerField(blank=True, null=True)),
                ('highest_rank', models.IntegerField(blank=True, null=True)),
                ('highest_rank_week', models.IntegerField(blank=True, null=True)),
                ('weeks_in_top_3', models.IntegerField(default=0)),
                ('weeks_in_top_5', models.IntegerField(default=0)),
                ('weeks_as_leader', models.IntegerField(default=0)),
                ('favorite_team_picked', models.CharField(blank=True, max_length=50)),
                ('favorite_team_pick_count', models.IntegerField(default=0)),
                ('most_successful_category', models.CharField(blank=True, max_length=20)),
                ('trending_direction', models.CharField(choices=[('up', 'Trending Up'), ('down', 'Trending Down'), ('stable', 'Stable')], default='stable', max_length=10)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='weeklysnapshot',
            constraint=models.UniqueConstraint(fields=('user', 'week'), name='unique_user_week_snapshot'),
        ),
        migrations.AddConstraint(
            model_name='rankhistory',
            constraint=models.UniqueConstraint(fields=('user', 'week'), name='unique_user_week_rank'),
        ),
        migrations.AddConstraint(
            model_name='leaderboardsnapshot',
            constraint=models.UniqueConstraint(fields=('week',), name='unique_week_leaderboard'),
        ),
    ]