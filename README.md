# Smart Campus, Smart Bus

Smart Campus, Smart Bus is a Django-based smart transportation system designed for campus environments. It helps students, drivers, and administrators manage daily transport operations through live tracking, seat booking, route visibility, and operational monitoring in one unified dashboard.

## Description

This project provides a modern smart transport platform for campus bus services. It combines booking, tracking, scheduling, role-based access, and admin monitoring tools with a clean dark-themed dashboard experience.

## Features

- Live bus tracking dashboard
- Seat booking system for authenticated users
- Role-based authentication for students, drivers, and admins
- Bus schedule and route management
- Fuel monitoring and operational visibility
- Alerts and monitoring dashboard for admins
- Analytics dashboard for transport insights
- Modern dark-themed responsive UI
- Map integration support using Leaflet or a similar mapping library

## Tech Stack

- Backend: Django
- Frontend: Django Templates, HTML, CSS, JavaScript
- Database: PostgreSQL for production, SQLite for development
- Mapping: Leaflet or similar map integration
- Authentication: Django authentication with role-based access

## Project Structure

```text
Smart Campus Smart Transport/
├── apps/
│   ├── booking/
│   ├── core/
│   ├── dashboard/
│   ├── fuel/
│   ├── routing/
│   └── tracking/
├── smartbus/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── static/
│   ├── css/
│   └── js/
├── templates/
├── manage.py
├── requirements.txt
└── README.md
```

## Installation Guide

1. Clone the repository:

```bash
git clone https://github.com/your-username/smart-campus-smart-bus.git
cd smart-campus-smart-bus
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create an environment file from `.env.example` and configure variables such as:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=127.0.0.1,localhost
```

For PostgreSQL, use a `DATABASE_URL` similar to:

```env
DATABASE_URL=postgres://username:password@localhost:5432/smartbus
```

5. Run migrations:

```bash
python manage.py migrate
```

6. Create a superuser:

```bash
python manage.py createsuperuser
```

## Usage

Start the development server with:

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

## Environment Variables

The project now reads deployment-sensitive settings from environment variables.

Required in production:

- `SECRET_KEY`
- `DEBUG`
- `DATABASE_URL`

Commonly used:

- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `EMAIL_BACKEND`
- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS`
- `DEFAULT_FROM_EMAIL`
- `TRACKING_SHARED_API_KEY`
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

Render also provides `RENDER_EXTERNAL_HOSTNAME`, which the project automatically uses for `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

## Render Deployment

This repository includes:

- `render.yaml` for Render Blueprint deployment
- `Procfile` for WSGI process declaration
- WhiteNoise static file serving
- Gunicorn production serving
- PostgreSQL-ready `DATABASE_URL` configuration

Recommended Render web service settings:

```text
Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
Start Command: gunicorn smartbus.wsgi:application
```

If you use the included `render.yaml`, Render can provision:

- a PostgreSQL database
- a Python web service
- generated `SECRET_KEY`
- `DATABASE_URL` wiring from the managed database

The project can also bootstrap the first superuser automatically on app startup if these environment variables are set:

```env
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=choose-a-strong-password
```

Behavior:

- if no superuser exists, one is created
- if a superuser already exists, nothing happens
- if any of the variables are missing, bootstrap is skipped safely

## Local Development After Deployment Changes

Local development still works with SQLite by default if `DATABASE_URL` is not set.

Typical local `.env`:

```env
DEBUG=True
SECRET_KEY=dev-secret-key
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=127.0.0.1,localhost
```

## Authentication & Roles

The system supports role-based access control:

- Student: Book seats, view schedules, and track buses live
- Driver: Access assigned route and transport-related operational views
- Admin: Manage dashboards, alerts, monitoring, analytics, and system-level tools

Authentication is handled through Django's built-in auth system, with role-specific access layered on top for each user type.

## Future Improvements

- Real-time GPS integration for bus movement
- Push notifications for delays and alerts
- QR-based ticket validation
- Mobile-first passenger dashboard
- Advanced reporting and export tools

## License

This project is provided for academic, hackathon, and learning purposes. Add a project license here before production or public distribution.
