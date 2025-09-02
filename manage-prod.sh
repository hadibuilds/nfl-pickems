#!/bin/bash
# Production Django Management Script for NFL Pickems

CLUSTER="nfl-pickems-cluster"
SERVICE="nfl-pickems-service"
REGION="us-east-2"
CONTAINER="nfl-pickems-backend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏈 NFL Pickems Production Management${NC}"

# Function to get current task ID
get_task_id() {
    aws ecs list-tasks --cluster $CLUSTER --service-name $SERVICE --region $REGION --query 'taskArns[0]' --output text | cut -d'/' -f3
}

# Function to run Django management command
run_django_command() {
    local cmd="$1"
    echo -e "${YELLOW}Running: python manage.py $cmd${NC}"
    
    aws ecs run-task \
        --cluster $CLUSTER \
        --task-definition nfl-pickems-task \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[subnet-0b7b7242cf2063121,subnet-01c71c4a9db01d389,subnet-0818ab15d07a51509],securityGroups=[sg-01223191c20daecbc],assignPublicIp=ENABLED}" \
        --overrides "{\"containerOverrides\":[{\"name\":\"$CONTAINER\",\"command\":[\"python\",\"manage.py\",\"$cmd\"]}]}" \
        --region $REGION
}

# Function to connect to running container
shell_access() {
    local task_id=$(get_task_id)
    if [ "$task_id" == "None" ]; then
        echo -e "${RED}❌ No running tasks found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}🔗 Connecting to task: $task_id${NC}"
    aws ecs execute-command \
        --cluster $CLUSTER \
        --task $task_id \
        --container $CONTAINER \
        --interactive \
        --command "/bin/bash" \
        --region $REGION
}

# Main menu
case "$1" in
    "shell")
        shell_access
        ;;
    "populate-games")
        run_django_command "populate_nfl_games --limit=0"
        ;;
    "migrate")
        run_django_command "migrate"
        ;;
    "collectstatic")
        run_django_command "collectstatic --noinput"
        ;;
    "createsuperuser")
        echo -e "${YELLOW}Creating superuser via shell access...${NC}"
        shell_access
        ;;
    *)
        echo -e "${YELLOW}Usage:${NC}"
        echo "  $0 shell              - Connect to running container"
        echo "  $0 populate-games     - Populate NFL games"
        echo "  $0 migrate            - Run database migrations"
        echo "  $0 collectstatic      - Collect static files"
        echo "  $0 createsuperuser    - Create superuser (opens shell)"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo "  $0 shell"
        echo "  $0 populate-games"
        ;;
esac