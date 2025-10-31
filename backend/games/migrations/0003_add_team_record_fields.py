# Generated migration to add team record fields to Game model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0002_allow_tie_winner'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='home_team_record',
            field=models.CharField(blank=True, default='', help_text='W-L or W-L-T', max_length=20),
        ),
        migrations.AddField(
            model_name='game',
            name='away_team_record',
            field=models.CharField(blank=True, default='', help_text='W-L or W-L-T', max_length=20),
        ),
    ]
