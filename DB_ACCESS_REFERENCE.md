# NFL Pickems Database Access Reference

## Quick Access Commands

### 🚀 Run Django Commands in Production
```bash
# Get current running task ID
TASK_ID=$(aws ecs list-tasks --cluster nfl-pickems-cluster --region us-east-2 --query 'taskArns[0]' --output text | cut -d'/' -f3)

# Run one-time command (creates new task)
aws ecs run-task \
  --cluster nfl-pickems-cluster \
  --task-definition nfl-pickems-task:22 \
  --launch-type FARGATE \
  --network-configuration 'awsvpcConfiguration={subnets=[subnet-0b7b7242cf2063121,subnet-01c71c4a9db01d389,subnet-0818ab15d07a51509],securityGroups=[sg-01223191c20daecbc],assignPublicIp=ENABLED}' \
  --overrides '{"containerOverrides":[{"name":"nfl-pickems-backend","command":["python","manage.py","COMMAND_HERE"]}]}' \
  --region us-east-2
```

### 📊 Data Population Commands
```bash
# Populate NFL games (historical data)
python manage.py populate_nfl_games --limit=0 --settings=nfl_pickems.settings

# Create mock data for testing
python manage.py create_mock_nfl_data

# Verify data was created
python manage.py shell -c "from games.models import Game, Window; print(f'Games: {Game.objects.count()}, Windows: {Window.objects.count()}')"
```

### 🔍 Database Inspection Commands
```bash
# Django shell
python manage.py shell

# Check database contents
python manage.py shell -c "
from games.models import Game, Window
from predictions.models import MoneyLinePrediction, PropBetPrediction
from django.contrib.auth import get_user_model
User = get_user_model()

print('=== DATABASE SUMMARY ===')
print(f'Users: {User.objects.count()}')
print(f'Games: {Game.objects.count()}')
print(f'Windows: {Window.objects.count()}')
print(f'ML Predictions: {MoneyLinePrediction.objects.count()}')
print(f'Prop Predictions: {PropBetPrediction.objects.count()}')
"

# List all users
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
for user in User.objects.all():
    print(f'{user.username} ({user.email}) - {user.first_name} {user.last_name}')
"

# Check latest games
python manage.py shell -c "
from games.models import Game
for game in Game.objects.order_by('-start_time')[:5]:
    print(f'{game.away_team} @ {game.home_team} - Week {game.week} - {game.start_time}')
"
```

### 🛠️ Utility Commands
```bash
# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser

# Check system health
python manage.py check --deploy
```

### 📋 Task Monitoring
```bash
# List all tasks
aws ecs list-tasks --cluster nfl-pickems-cluster --region us-east-2

# Check task status
aws ecs describe-tasks --cluster nfl-pickems-cluster --tasks TASK_ID --region us-east-2 --query 'tasks[0].lastStatus'

# View logs
aws logs tail /ecs/nfl-pickems-task --region us-east-2 --follow

# View specific task logs
aws logs tail /ecs/nfl-pickems-task --region us-east-2 --filter-pattern "TASK_ID"
```

## 📝 One-Liner Examples

### Quick Data Check
```bash
aws ecs run-task --cluster nfl-pickems-cluster --task-definition nfl-pickems-task:22 --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[subnet-0b7b7242cf2063121],securityGroups=[sg-01223191c20daecbc],assignPublicIp=ENABLED}' --overrides '{"containerOverrides":[{"name":"nfl-pickems-backend","command":["python","manage.py","shell","-c","from games.models import Game; print(f\"Games: {Game.objects.count()}\")"]}]}' --region us-east-2
```

### Populate Data
```bash
aws ecs run-task --cluster nfl-pickems-cluster --task-definition nfl-pickems-task:22 --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[subnet-0b7b7242cf2063121],securityGroups=[sg-01223191c20daecbc],assignPublicIp=ENABLED}' --overrides '{"containerOverrides":[{"name":"nfl-pickems-backend","command":["python","manage.py","populate_nfl_games","--limit=0","--settings=nfl_pickems.settings"]}]}' --region us-east-2
```

### Run Migrations
```bash
aws ecs run-task --cluster nfl-pickems-cluster --task-definition nfl-pickems-task:22 --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[subnet-0b7b7242cf2063121],securityGroups=[sg-01223191c20daecbc],assignPublicIp=ENABLED}' --overrides '{"containerOverrides":[{"name":"nfl-pickems-backend","command":["python","manage.py","migrate"]}]}' --region us-east-2
```

## 🔧 Environment Variables
Your production environment uses these key settings:
- `DJANGO_ENV=prod`
- `DEBUG=False`
- Database via `DATABASE_URL`
- Static files via WhiteNoise
- Media files via S3 (if `USE_CLOUD_STORAGE=true`)

## 📊 Key URLs for Testing
- **API Base**: https://api.pickems.fun
- **Frontend**: https://pickems.fun
- **Login**: https://api.pickems.fun/accounts/api/login/
- **Health Check**: https://api.pickems.fun/healthz
- **Analytics**: https://api.pickems.fun/analytics/api/stats-summary/

## 🆘 Troubleshooting
1. **Task won't start**: Check CloudWatch logs
2. **Database issues**: Verify DATABASE_URL environment variable
3. **Static files missing**: Run collectstatic
4. **No data**: Run populate_nfl_games command
5. **Authentication errors**: Check CORS/CSRF settings