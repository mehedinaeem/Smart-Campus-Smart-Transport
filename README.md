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

4. Create an environment file and configure variables such as:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
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
