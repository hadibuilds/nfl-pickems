#!/usr/bin/env python
import os, sys, django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nfl_pickems.settings.dev')
django.setup()

from predictions.utils.dashboard_utils import get_current_week
from games.models import Game

current_week = get_current_week()
actual_weeks = list(Game.objects.values_list('week', flat=True).distinct().order_by('week'))

print(f"🔍 CURRENT WEEK ANALYSIS")
print(f"Current week calculation: {current_week}")
print(f"Actual weeks in database: {actual_weeks}")
print(f"Problem: Current week {current_week} {'exists' if current_week in actual_weeks else 'DOES NOT EXIST'} in database")