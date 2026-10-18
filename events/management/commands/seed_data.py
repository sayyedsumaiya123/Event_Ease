"""
Management command to seed initial demo data for EventEase.
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify
from datetime import date, time, timedelta
import random

from events.models import Event, Category, Registration


CATEGORIES = [
    {'name': 'Technology', 'slug': 'technology', 'icon': 'bi-cpu', 'color': '#6366f1'},
    {'name': 'Hackathon',  'slug': 'hackathon',  'icon': 'bi-code-square', 'color': '#8b5cf6'},
    {'name': 'Workshop',   'slug': 'workshop',   'icon': 'bi-tools', 'color': '#10b981'},
    {'name': 'Cultural',   'slug': 'cultural',   'icon': 'bi-music-note-beamed', 'color': '#f59e0b'},
    {'name': 'Sports',     'slug': 'sports',     'icon': 'bi-trophy', 'color': '#ef4444'},
    {'name': 'AI & ML',    'slug': 'ai-ml',      'icon': 'bi-robot', 'color': '#38bdf8'},
    {'name': 'Business',   'slug': 'business',   'icon': 'bi-briefcase', 'color': '#ec4899'},
    {'name': 'Science',    'slug': 'science',    'icon': 'bi-flask', 'color': '#a78bfa'},
]

EVENTS = [
    {
        'title': 'Tech Fest 2026',
        'description': 'The biggest technology festival of the year! Join us for 3 days of talks, workshops, and networking with industry leaders from top tech companies. Topics include AI, cloud computing, DevOps, blockchain, and emerging technologies.',
        'venue': 'College Auditorium',
        'capacity': 500,
        'days': 5,
        'time': '10:00',
        'end_time': '18:00',
        'category': 'Technology',
        'featured': True,
        'status': 'upcoming',
    },
    {
        'title': '24-Hour Hackathon',
        'description': 'Code your way to victory! Teams of 2–4 students compete to build innovative solutions for real-world problems. Exciting prizes worth ₹50,000 await the winners. Food and refreshments provided throughout.',
        'venue': 'CS Lab, Block B',
        'capacity': 200,
        'days': 12,
        'time': '09:30',
        'end_time': '22:30',
        'category': 'Hackathon',
        'featured': True,
        'status': 'upcoming',
    },
    {
        'title': 'AI & Machine Learning Workshop',
        'description': 'A hands-on workshop on Artificial Intelligence and Machine Learning. Learn about neural networks, TensorFlow, PyTorch, and build your first ML model. Beginner-friendly with expert guidance throughout.',
        'venue': 'Seminar Hall 1',
        'capacity': 80,
        'days': 8,
        'time': '11:00',
        'end_time': '15:00',
        'category': 'AI & ML',
        'featured': True,
        'status': 'upcoming',
    },
    {
        'title': 'Annual Sports Meet',
        'description': 'The annual inter-college sports competition featuring cricket, football, basketball, volleyball, badminton, and athletics. Come support your college team and participate in individual events!',
        'venue': 'Sports Ground',
        'capacity': 1000,
        'days': 15,
        'time': '08:30',
        'end_time': '17:30',
        'category': 'Sports',
        'featured': False,
        'status': 'upcoming',
    },
    {
        'title': 'DevOps Masterclass',
        'description': 'A comprehensive masterclass on DevOps practices. Topics: Git, CI/CD with Jenkins, Docker containerization, Kubernetes orchestration, and monitoring with Prometheus & Grafana. Industry experts as speakers.',
        'venue': 'IT Department Seminar Hall',
        'capacity': 100,
        'days': 20,
        'time': '13:00',
        'end_time': '17:00',
        'category': 'Technology',
        'featured': True,
        'status': 'upcoming',
    },
    {
        'title': 'Cultural Night 2026',
        'description': 'Celebrate diversity with an evening of music, dance, drama, and art. Students showcase their cultural heritage through performances. Followed by a grand dinner and DJ night.',
        'venue': 'Open Air Theatre',
        'capacity': 800,
        'days': 18,
        'time': '18:30',
        'end_time': '22:30',
        'category': 'Cultural',
        'featured': False,
        'status': 'upcoming',
    },
    {
        'title': 'Web Development Bootcamp',
        'description': 'Intensive 2-day bootcamp covering HTML, CSS, JavaScript, React, Django, and deployment. Build a complete full-stack web application from scratch. Certificate of completion awarded.',
        'venue': 'Computer Lab 3',
        'capacity': 50,
        'days': 25,
        'time': '09:00',
        'end_time': '16:00',
        'category': 'Workshop',
        'featured': False,
        'status': 'upcoming',
    },
    {
        'title': 'Startup Pitch Competition',
        'description': 'Present your startup idea to a panel of investors and industry experts. Get mentorship, feedback, and a chance to win seed funding up to ₹1,00,000. Open to all students and recent graduates.',
        'venue': 'Business School Auditorium',
        'capacity': 150,
        'days': 30,
        'time': '14:00',
        'end_time': '18:00',
        'category': 'Business',
        'featured': True,
        'status': 'upcoming',
    },
    {
        'title': 'Cloud Computing Seminar',
        'description': 'Expert session on AWS, Google Cloud, and Azure. Learn about cloud architecture, microservices, serverless computing, and cost optimization strategies. Live demos included.',
        'venue': 'Online + Main Auditorium',
        'capacity': 300,
        'days': -5,
        'time': '15:00',
        'end_time': '17:00',
        'category': 'Technology',
        'featured': False,
        'status': 'completed',
    },
    {
        'title': 'Data Science Symposium',
        'description': 'Research paper presentations and expert talks on Data Science, Big Data, and Analytics. Open for paper submissions from students and faculty. Best paper award sponsored by TCS.',
        'venue': 'Conference Hall',
        'capacity': 200,
        'days': -10,
        'time': '10:30',
        'end_time': '16:30',
        'category': 'Science',
        'featured': False,
        'status': 'completed',
    },
    {
        'title': 'Campus Design Sprint',
        'description': 'A focused design sprint for students and creators to ideate, prototype, and pitch real product concepts. Includes mentorship from UI/UX mentors and product designers.',
        'venue': 'Innovation Center Hall',
        'capacity': 120,
        'days': 3,
        'time': '17:00',
        'end_time': '20:30',
        'category': 'Technology',
        'featured': True,
        'status': 'upcoming',
    },
]


class Command(BaseCommand):
    help = 'Seed the database with demo data for EventEase'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('\nSeeding EventEase database...\n'))

        Registration.objects.all().delete()
        Event.objects.all().delete()

        # Create admin if not exists
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser('admin', 'admin@eventease.com', 'Admin@123')
            admin.first_name = 'EventEase'
            admin.last_name = 'Admin'
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created admin user: admin / Admin@123'))

        admin = User.objects.get(username='admin')

        # Create regular test users
        test_users = []
        for i in range(1, 6):
            username = f'user{i}'
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@test.com',
                    password='Test@1234',
                    first_name=f'Test',
                    last_name=f'User{i}'
                )
                test_users.append(user)
                self.stdout.write(f'  Created user: {username} / Test@1234')
            else:
                test_users.append(User.objects.get(username=username))

        # Create categories
        category_map = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            category_map[cat_data['name']] = cat
            if created:
                self.stdout.write(f'  Created category: {cat.name}')

        self.stdout.write(self.style.SUCCESS(f'{len(CATEGORIES)} categories ready'))

        # Create events
        event_count = 0
        for ev_data in EVENTS:
            slug = slugify(ev_data['title'])
            event_date = date.today() + timedelta(days=ev_data['days'])
            event_start = time.fromisoformat(ev_data['time'])
            event_end = time.fromisoformat(ev_data['end_time'])

            event = Event.objects.create(
                title=ev_data['title'],
                slug=slug,
                description=ev_data['description'],
                short_description=ev_data['description'][:200] + '...',
                category=category_map.get(ev_data['category']),
                date=event_date,
                time=event_start,
                end_time=event_end,
                venue=ev_data['venue'],
                venue_address=f'{ev_data["venue"]}, Main Campus, College Road',
                capacity=ev_data['capacity'],
                status=ev_data['status'],
                featured=ev_data['featured'],
                is_free=True,
                organizer=admin,
                tags=f'{ev_data["category"].lower()}, event, college',
            )

            # Add some registrations for upcoming events
            if ev_data['status'] == 'upcoming':
                num_regs = random.randint(5, min(30, ev_data['capacity']))
                users_to_register = random.sample(test_users, min(num_regs, len(test_users)))
                for user in users_to_register:
                    Registration.objects.get_or_create(
                        user=user, event=event,
                        defaults={'status': 'confirmed'}
                    )

            event_count += 1

        self.stdout.write(self.style.SUCCESS(f'{event_count} events created'))

        self.stdout.write(self.style.SUCCESS(
            '\nDatabase seeded successfully!\n'
            'Admin:  admin / Admin@123\n'
            'Users:  user1-5 / Test@1234\n'
            f'Events: {event_count} events created\n'
            'Visit:  http://localhost:8000\n'
        ))
