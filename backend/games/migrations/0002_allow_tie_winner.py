# Generated migration to allow TIE as a valid winner value

from django.db import migrations, models
from django.db.models import Q, F


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='game',
            name='chk_winner_is_team',
        ),
        migrations.AddConstraint(
            model_name='game',
            constraint=models.CheckConstraint(
                check=(
                    Q(winner__isnull=True) |
                    Q(winner=F("home_team")) |
                    Q(winner=F("away_team")) |
                    Q(winner="TIE")
                ),
                name='chk_winner_is_team',
            ),
        ),
    ]
