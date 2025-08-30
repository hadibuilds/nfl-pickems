# Project Cleanup Analysis

## Django Apps Analysis

### ✅ **KEEP - Active Apps**
1. **accounts** - User authentication, registration ✅
2. **games** - Game data, windows, prop bets ✅  
3. **predictions** - User predictions (CRUD only) ✅
4. **analytics** - Data analysis, stats, leaderboards ✅
5. **frontend** - Serves React app via Django templates ✅

### ❌ **UNUSED - None Found**
All apps are being used and serve specific purposes.

## File Cleanup Targets

### 🗑️ **Definitely Delete**
```bash
# Python cache files (3340+ files)
find . -name "__pycache__" -type d
find . -name "*.pyc"

# Node modules in backend (shouldn't exist)
backend/node_modules/

# IDE files
.DS_Store files
.vscode/ settings (if not needed)

# Build artifacts
*.log files
*.tmp files
```

### 📁 **Frontend Build Analysis** 
```bash
frontend/dist/           # Built React app
frontend/node_modules/   # Dependencies (large)
backend/static/assets/   # Compiled React assets served by Django
```

### 🤔 **Potential Cleanup Candidates**
```bash
# Test files that might be unused
backend/test_*.py files
backend/*/test_*.py files

# Migration files for development
backend/*/migrations/0001_initial.py (check if needed)

# Templates we might not use
backend/templates/registration/ (password reset templates)

# CSS files in frontend/src/
RecentGamesScrollbar.css (specific hack - may be unused)
```

## Archive Directory Structure
```
_archive/
├── optimization-migration/
│   ├── CLEANUP_ANALYSIS.md
│   ├── OPTIMIZATION_MIGRATION_GUIDE.md  
│   ├── CLEANUP_COMPLETE_SUMMARY.md
│   ├── views_legacy_backup.py
│   ├── urls_legacy_backup.py
│   └── consolidated_dashboard_utils.py
├── unused-files/
│   └── (files we remove but want to keep)
└── development-artifacts/
    └── (test files, temp files, etc.)
```

## Size Analysis
```bash
# Large directories
frontend/node_modules/     # ~500MB+ (development dependencies)
backend/static/            # Compiled assets
venv_pickems/             # Python virtual environment
```

## Cleanup Strategy

### Phase 1: Safe Cleanup ✅
- Remove Python cache files
- Remove .DS_Store files  
- Clean up IDE artifacts

### Phase 2: Development Cleanup
- Move test files to archive
- Clean up unused imports
- Remove temporary files

### Phase 3: Build Optimization  
- Verify frontend build process
- Clean up unused CSS
- Optimize static assets