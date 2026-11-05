# EventEase — Containerized Event Management System with DevOps CI/CD Pipeline

> **"EventEase: A Containerized Event Management System with Automated CI/CD and DevOps Monitoring"**

[![CI/CD Pipeline](https://github.com/YOUR_USERNAME/event-management/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/YOUR_USERNAME/event-management/actions)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)](https://hub.docker.com)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django)](https://djangoproject.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)

---

## 📋 Project Overview

**EventEase** is a full-featured event management web application built with Django, containerized with Docker, and deployed through a complete DevOps CI/CD pipeline. This project demonstrates the complete software delivery lifecycle:

```
Plan → Code → Git → Test → Quality Check → Dockerize → Push Image → Deploy → Monitor
```

---

## 🏗️ Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript |
| Backend | Django 5.0 (Python 3.12) |
| Database | PostgreSQL 16 |
| Version Control | Git + GitHub |
| Containerization | Docker + Docker Compose |
| CI/CD | Jenkins + GitHub Actions |
| Image Registry | Docker Hub |
| Web Server | Nginx (Reverse Proxy) |
| Monitoring | Prometheus + Grafana |
| Testing | Django TestCase + Coverage.py |
| Code Quality | Flake8 + Bandit |
| Infrastructure | Docker Compose |

---

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.12+
- Git

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/event-management.git
cd event-management
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run migrations
```bash
python manage.py migrate
```

### 5. Seed demo data
```bash
python manage.py seed_data
```

### 6. Run the server
```bash
python manage.py runserver
```

Visit: **http://localhost:8000**

**Demo credentials:**
- Admin: `admin` / `Admin@123`
- User: `user1` / `Test@1234`

---

## 🐳 Docker Deployment

### Run with Docker Compose (Full Stack)

```bash
# Copy environment file
copy .env.example .env

# Start all services
docker compose up -d

# Seed data
docker compose exec web python manage.py seed_data
```

Services started:
| Service | Port | URL |
|---------|------|-----|
| Web Application | 80 | http://localhost |
| Django (Gunicorn) | 8000 | (proxied by Nginx) |
| PostgreSQL | 5432 | internal |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3000 | http://localhost:3000 |

---

## 🧪 Running Tests

```bash
# Run all tests
python manage.py test --verbosity=2

# Run with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generates htmlcov/ directory
```

### Test Coverage Areas
- ✅ Model behavior (Event, Registration, Category)
- ✅ View access control (login required, staff required)
- ✅ Event registration logic (success, duplicate, full, waitlist)
- ✅ Admin panel access control
- ✅ User authentication flows

---

## 🔄 CI/CD Pipeline

### GitHub Actions (`.github/workflows/ci-cd.yml`)

```
Push to GitHub
     ↓
[Job 1] Run Tests (with PostgreSQL)
     ↓
[Job 2] Code Quality (Flake8 + Bandit)
     ↓
[Job 3] Docker Build & Push to Docker Hub
     ↓
[Job 4] SSH Deploy to Production Server
```

### Jenkins Pipeline (`Jenkinsfile`)

```
Checkout → Setup Python → Run Tests → Coverage Check
    → SonarQube Analysis → Docker Build → Docker Push
    → Deploy → Health Check
```

---

## 🗄️ Database Schema

```
User ──────────── Registration ──────────── Event
  │                     │                     │
  └── UserProfile        └── ticket_number     └── Category
                                               └── EventFeedback
```

**Tables:** User, UserProfile, Category, Event, Registration, EventFeedback

---

## 📁 Project Structure

```
event-management/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── Jenkinsfile
├── pytest.ini
├── .env.example
├── .gitignore
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml          ← GitHub Actions Pipeline
│
├── event_management/          ← Django project config
│   ├── settings.py
│   ├── settings_prod.py
│   ├── urls.py
│   └── wsgi.py
│
├── events/                    ← Core event app
│   ├── models.py              ← Event, Category, Registration
│   ├── views.py               ← All views
│   ├── urls.py
│   ├── forms.py
│   ├── admin.py
│   └── tests.py               ← Automated tests
│
├── accounts/                  ← User auth app
│   ├── models.py              ← UserProfile
│   ├── views.py
│   ├── urls.py
│   └── forms.py
│
├── templates/                 ← HTML templates
├── static/                    ← CSS, JS
├── nginx/                     ← Nginx config
└── monitoring/                ← Prometheus + Grafana configs
```

---

## 🏛️ Architecture

```
                  USERS
                    │
                    ▼
              ┌─────────────┐
              │   Browser   │
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │    Nginx    │  ← Reverse Proxy
              │   Port 80   │  ← Serves Static Files
              └──────┬──────┘
                     │
                     ▼
       ┌─────────────────────────────┐
       │     Django + Gunicorn       │
       │      Docker Container       │
       └──────────────┬──────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  PostgreSQL   │
              │ Docker Volume │
              └───────────────┘

         DEVOPS PIPELINE

Developer → GitHub → Jenkins/GitHub Actions
    → Tests → SonarQube → Docker Build
    → Docker Hub → Server → Live App
    → Prometheus → Grafana → Alerts
```

---

## 📊 Monitoring

After `docker compose up`:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/Admin@123)
  - Import dashboard ID **9528** for Django metrics

Metrics exposed at: `http://localhost:8000/metrics`

---

## 🎓 Viva Points

| Question | Answer |
|----------|--------|
| Why DevOps? | Automates the complete software delivery lifecycle |
| Why Docker? | Consistent environment across dev, test, prod |
| Why Jenkins? | Automates CI/CD — triggers pipeline on every push |
| Why PostgreSQL? | Relational DB for structured User→Event→Registration data |
| Why Prometheus? | Collects metrics from the live application |
| Why Grafana? | Visualizes metrics in real-time dashboards |
| Why Nginx? | Handles HTTP, reverse proxy, static files, HTTPS |

---

## 👥 Features

### User Side
- Register / Login / Profile
- Browse & search events
- Filter by category, date, status
- View event details with seat availability
- Register for events (auto ticket generation)
- Cancel registration
- Personal dashboard

### Admin Panel
- Dashboard with KPIs
- Create / Edit / Delete events
- View participants per event
- Manage users (activate/deactivate)

---

## 📄 License

This project is built for educational purposes as a DevOps college project.

---

*Built with ❤️ by the EventEase Team | Django + Docker + Jenkins + Prometheus + Grafana*


### Phone check-in on a local network

The organizer displays an attendance QR and each attendee scans it with their phone camera, signs in, and confirms check-in. The QR expires after five minutes; generate another from the attendance dashboard when needed. Organizers can download a CSV of confirmed participants and attendance.

For local testing, connect the computer and phones to the same network. Find the computer's LAN IP using `ipconfig`, add that IP to `ALLOWED_HOSTS` in your environment, run `python manage.py runserver 0.0.0.0:8000`, and open `http://<computer-LAN-IP>:8000` on the organizer's computer before generating the QR. `localhost` points to each device itself and will not work across devices. Network isolation or a firewall may also prevent connections. Use a reachable HTTPS domain in production.

### Coordinator applications and event access

Organizers can review coordinator applications in the Coordinator Panel. Approved coordinators can create events or manage events explicitly assigned to them. Organizers assign coordinators when creating or editing an event; the panel lists the assignments for their own events. A superuser can designate organizer reviewers using the `is_organizer` field on a user's profile in Django admin. The user must also be active and have staff status. Existing staff accounts without coordinator applications were marked as organizers during the migration; review those roles when upgrading a populated database.


### Event Passport and certificates

Participants can open My Event Passport from My Events to see confirmed registrations with recorded check-ins, a category summary, and a CSV export. Organizers can enable participation certificates when creating or editing an event. Eligible participants can download a PDF certificate containing a QR code and clickable verification link. Verification returns unavailable when the event is cancelled, certificates are disabled, the registration is no longer confirmed, or the attendance record is removed.

The verification URL uses the address from which the certificate was downloaded. Use a stable, publicly reachable HTTPS domain if other people need to verify certificates; local addresses and temporary tunnels will not remain accessible to external verifiers. A shared QR check-in records an action but does not independently establish physical presence.
