from django import forms
from .models import Prediction
from games.models import Game

class PredictionForm(forms.ModelForm):
    class Meta:
        model = Prediction
        fields = ['predicted_winner']

    def __init__(self, *args, **kwargs):
        game = kwargs.pop('game', None)
        super().__init__(*args, **kwargs)
        if game:
            self.fields['predicted_winner'].choices = [
                (game.home_team, game.home_team),
                (game.away_team, game.away_team),
            ]
