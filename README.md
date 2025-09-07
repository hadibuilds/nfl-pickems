# NFL Pickems

A comprehensive NFL prediction platform where users make weekly picks on games and prop bets, compete on leaderboards, and track their performance throughout the season.

## 🏈 Features

### Core Functionality
- **Weekly Game Predictions**: Pick winners for NFL games organized by time windows (morning, afternoon, late)
- **Prop Bet Predictions**: Answer various prop bet questions including over/under, point spreads, and "take-the-bait" scenarios
- **Real-time Scoring**: Automatic grading of predictions when game results are finalized
- **Leaderboard System**: Weekly rankings and season-long competition tracking

### User Experience
- **Responsive Design**: Optimized for desktop and mobile devices
- **Profile Management**: User avatars, display names, and personal statistics
- **Progressive Submission**: Save draft picks and submit when ready
- **Performance Analytics**: Detailed statistics on accuracy, trends, and achievements

### Administrative Features
- **Game Management**: Import games, set windows, and finalize results
- **Prediction Analytics**: Comprehensive stats tracking and historical data
- **User Administration**: Account management and moderation tools

## 🏗️ Architecture

### Backend (Django REST API)
- **Framework**: Django 4.x with Django REST Framework
- **Database**: PostgreSQL with optimized indexing
- **Authentication**: Session-based authentication with CSRF protection
- **Storage**: Configurable local/S3 storage for user avatars
- **Caching**: Redis caching for performance-critical queries

### Frontend (React SPA)
- **Framework**: React 18 with Vite build system
- **Styling**: Tailwind CSS for responsive design
- **State Management**: React Context for authentication and theme
- **API Integration**: Axios for REST API communication
- **Routing**: React Router for navigation

### Data Models
- **Users**: Custom user model with profile fields and avatar management
- **Games**: NFL games organized by season, week, and time windows
- **Predictions**: Money-line and prop bet predictions with correctness tracking
- **Analytics**: User performance history and season statistics
- **Windows**: Time-based game groupings for progressive revealing of results

## 🚀 Deployment Options

### Development
```bash
# Backend setup
cd backend
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend setup
cd frontend
npm install
npm run dev
```

### Production Options
- **AWS**: ECS with Fargate, RDS PostgreSQL, S3 storage
- **Render**: Integrated deployment with managed PostgreSQL
- **OpenShift**: Container platform deployment (see `pickems.md`)

## 📁 Project Structure

```
├── backend/              # Django API server
│   ├── accounts/         # User authentication and profiles
│   ├── games/            # Game and prop bet models
│   ├── predictions/      # User prediction models and views
│   ├── analytics/        # Statistics and leaderboard logic
│   └── nfl_pickems/     # Django project settings
├── frontend/            # React SPA
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/       # Route components
│   │   ├── context/     # React context providers
│   │   └── utils/       # Helper functions
├── aws/                # AWS deployment configurations
└── docs/               # Additional documentation
```

## 🛡️ Security Features

- CSRF protection on all state-changing operations
- Input validation and sanitization
- Secure session management
- Database constraint enforcement
- Timezone-aware datetime handling
- File upload validation and processing

## 📊 Key Features Detail

### Prediction System
- **Money-line Picks**: Choose the winning team for each game
- **Prop Bets**: Multiple choice questions with various categories
- **Locking Mechanism**: Predictions locked when games start
- **Validation**: Comprehensive input validation and constraint checking

### Scoring & Analytics
- **Real-time Updates**: Automatic scoring when games are finalized
- **Historical Tracking**: Complete prediction history with performance metrics
- **Leaderboards**: Weekly and season-long rankings
- **Achievement System**: Track personal bests and consistency metrics

### User Experience
- **Draft System**: Save picks before final submission
- **Progress Indicators**: Visual feedback on completion status
- **Responsive Design**: Optimized for all device sizes
- **Theme Support**: Light/dark mode toggle

## 🔧 Configuration

### Environment Variables
- `DJANGO_ENV`: Development or production mode
- `DATABASE_URL`: PostgreSQL connection string
- `DJANGO_SECRET_KEY`: Django secret key
- `USE_CLOUD_STORAGE`: Enable S3 storage for avatars
- `CORS_ALLOWED_ORIGINS`: Frontend URLs for CORS

### Database Setup
The application uses PostgreSQL with carefully designed indexes for performance:
- Game lookups by season/week/window
- User prediction queries
- Leaderboard generation
- Statistics calculations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For questions or issues:
1. Check existing GitHub issues
2. Create a new issue with detailed description
3. Include relevant logs and environment details

---

Built with ❤️ for NFL fans who love the thrill of prediction and competition!