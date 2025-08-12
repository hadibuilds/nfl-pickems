import requests

# Test fetching a single game from the references
single_game_url = "http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/401772510?lang=en&region=us"

response = requests.get(single_game_url)
print(f"Single game status: {response.status_code}")

if response.status_code == 200:
    game_data = response.json()
    print(f"Week: {game_data.get('week', {}).get('number')}")
    print(f"Date: {game_data.get('date')}")
    print(f"Name: {game_data.get('name')}")
    
    # Get team info
    competition = game_data.get('competitions', [{}])[0]
    competitors = competition.get('competitors', [])
    
    print("Teams:")
    for competitor in competitors:
        team_name = competitor.get('team', {}).get('displayName', '')
        home_away = competitor.get('homeAway', '')
        print(f"  {home_away}: {team_name}")
        
else:
    print(f"Failed: {response.text}")