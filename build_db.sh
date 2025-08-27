# move MV/special migrations aside
mkdir -p _hold
mv predictions/migrations/0002_* _hold/ 2>/dev/null || true
mv predictions/migrations/0003_* _hold/ 2>/dev/null || true

# ensure initial migrations exist
python backend/manage.py makemigrations games predictions insights
python backend/manage.py showmigrations

# build schema
python backend/manage.py migrate

# (optional) admin
python backend/manage.py createsuperuser

# bring MV migration back, set dependency to the real latest (likely 0001_initial)
mv _hold/0002_* predictions/migrations/ 2>/dev/null || true
mv _hold/0003_* predictions/migrations/ 2>/dev/null || true

# apply predictions extras
python backend/manage.py migrate predictions