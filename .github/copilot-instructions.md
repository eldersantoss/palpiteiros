# Project Guidelines

## Architecture

Django 5.0 monolith with following apps:

- **`accounts/`** — custom user registration/auth; extends Django's built-in auth views
- **`core/`** — domain logic: `Team`, `Competition`, `Match`, `GuessPool`, `Guesser`, `Guess`, `RankingEntry`

Each app (and consequently the entire project) follows the Django MTV architecture, which includes the following layers:

- **(M)odel:** it's the single definitive source of information about your data. It contains the essential fields and behaviors of the data you’re storing. Usually, each model maps to a single database table.
- **(T)amplate:** it's the presentation layer. It defines how the data should be displayed to the user. It’s mostly HTML mixed with Django Template Language (DTL) to insert dynamic content.
- **(V)iew:** it's the bridge between the Model and the Template. It accepts HTTP requests, applies the presentation logic (choosing what to display, what form to render, and where to redirect), and returns an HTTP response (usually by rendering a Template).

Data sync is driven by management commands in `core/management/commands/` (e.g., `create_and_update_matches`, `create_or_update_competitions`). Celery tasks in `core/tasks.py` wrap these commands for scheduled execution via `django-celery-beat`.

External football data comes from [api-sports.io](https://api-sports.io) through `core/services/football.py`, which implements `IFootballApi` from `core/services/interfaces.py`. Always use the interface when mocking in tests.

Infrastructure (PostgreSQL, Redis, Celery worker/beat) runs via `docker-compose.yml`. The Django dev server runs locally against those containers.

## Build and Test

```bash
# Setup (first time)
cp .env.example .env          # fill in values
docker compose up -d          # start DB/Redis/Celery
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate

# Run tests
pytest                        # uses --reuse-db by default
pytest --create-db            # required after model changes

# Run dev server
python manage.py runserver
```

## Code Style

- **black** with `line-length = 120`; **isort** with `profile = "black"`; **flake8** with `max-complexity = 7`
- All formatting config lives in `pyproject.toml`
- Class-based views only (see `core/views.py`); always use `LoginRequiredMixin` for authenticated views
- Base model: `TimeStampedModel` (adds `created`/`modified`); inherit from it for any new timestamped model
- Env vars via `python-decouple` (`config(...)`) — never hardcode secrets

## Project Conventions

- Models carry business logic as class/instance methods (e.g., `Competition.get_with_matches_on_period`, `pool.has_pending_match`)
- `data_source_id` on `Team`/`Competition`/`Match` maps to the external API's ID — don't confuse it with Django's `pk`
- Logo URLs are constructed dynamically from `data_source_id` (see `Team.logo_url`, `Competition.logo_url`)
- Management commands are the canonical way to trigger data sync; Celery tasks simply call `call_command(...)`
- pytest fixtures for domain objects live in `core/tests/conftest.py`; API response fixtures mock the api-sports.io shape
- Use a module-level logger (`logger = logging.getLogger(__name__)`) for significant user actions (e.g., submitting guesses, accessing sensitive routes).
- Log with enough context to reconstruct the event (timestamp, user, relevant data).

## Integration Points

- **api-sports.io** (RapidAPI): credentials via `FOOTBALL_API_KEY` / `FOOTBALL_API_HOST` env vars
- **Redis**: broker and result backend for Celery; also used as Django cache
- **PostgreSQL**: primary DB — use `docker compose up -d` before running anything locally
- **Email**: configured via `EMAIL_*` env vars; notification commands in `core/management/commands/`

## Security

- All core views require authentication — enforce with `LoginRequiredMixin` or `login_required`
- `GuessPoolMembershipMixin` (`core/viewmixins.py`) gates pool-scoped views; reuse it rather than reimplementing membership checks
- Superuser creation is scripted via `accounts/management/commands/createsuperuser_if_none_exists.py` (used in deployment)
