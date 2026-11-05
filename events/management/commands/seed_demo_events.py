from datetime import timedelta, time
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from shutil import copyfile
from django.utils.text import slugify
from events.models import Category, Event

EVENTS = [
    (
        'Midnight Code Heist',
        'Hackathon',
        '#a3e635',
        '#172016',
        4,
        'Innovation Lab',
        50,
        (
            'A night-long puzzle hackathon. Crack clues, build a tiny tool, and escape t'
            'he lab before sunrise. Bring a laptop; teams of up to four are welcome.'
        ),
    ),
    (
        'Cosmic Rooftop Silent Disco',
        'Music',
        '#ff88c8',
        '#351548',
        7,
        'Library Rooftop',
        120,
        (
            'Put on headphones and choose your universe: house, indie, or retro. Watch t'
            'he sky change colour while three DJs battle for your ears.'
        ),
    ),
    (
        'Robot Rumble: Battle of the Bots',
        'Technology',
        '#ff7448',
        '#202039',
        10,
        'Engineering Arena',
        80,
        (
            'Student-built robots enter a friendly obstacle arena. Expect wild designs, '
            'live commentary, and a build-and-drive challenge between rounds.'
        ),
    ),
    (
        'Glow-in-the-Dark Art Jam',
        'Art',
        '#8de2ff',
        '#172b55',
        13,
        'Studio 04',
        35,
        (
            'Make fluorescent posters, paint a collective mural, and trade mini prints u'
            'nder UV lights. All materials are included; beginners welcome.'
        ),
    ),
    (
        'The Great Campus Treasure Hunt',
        'Adventure',
        '#ffe47a',
        '#49311b',
        16,
        'Main Quad',
        60,
        (
            'Follow cryptic clues across campus, solve absurd challenges, and race the c'
            'lock. Form a team at the starting line or arrive with friends.'
        ),
    ),
    (
        'Murder Mystery at the Museum',
        'Culture',
        '#e6b3ed',
        '#39223b',
        20,
        'Heritage Hall',
        40,
        (
            'A priceless exhibit has vanished. Interview suspects, inspect clues, and wo'
            'rk out who did it over an immersive evening of theatre.'
        ),
    ),
    (
        'Zero Gravity Food Lab',
        'Food',
        '#ffc277',
        '#4c2320',
        25,
        'Culinary Studio',
        24,
        (
            'Experiment with edible bubbles, surprising textures, and impossible-looking'
            ' desserts in a hands-on food science workshop.'
        ),
    ),
    (
        'Indie Games After Dark',
        'Games',
        '#75f4d5',
        '#1b3043',
        29,
        'Student Activity Centre',
        90,
        (
            'Play weird and wonderful student-made games, meet their creators, and vote '
            'for the crowd favourite. Controllers and snacks provided.'
        ),
    ),
]


class Command(BaseCommand):
    help = 'Add non-destructive sample events for testing.'

    def handle(self, *args, **options):
        organizer, created = User.objects.get_or_create(
            username='eventease_demo',
            defaults={'email': 'demo@example.com', 'first_name': 'EventEase Demo', 'is_staff': True},
        )
        if created:
            organizer.set_password('EventDemo@123')
            organizer.save()
        media = Path(settings.MEDIA_ROOT) / 'events' / 'demo'
        media.mkdir(parents=True, exist_ok=True)
        for i, (title, category_name, accent, background, days, venue, capacity, description) in enumerate(EVENTS):
            category, _ = Category.objects.get_or_create(
                slug=category_name.lower(), defaults={'name': category_name, 'color': accent}
            )
            slug = 'demo-' + slugify(title)
            filename = 'photo-' + slugify(title) + '.jpg'
            copyfile(Path(settings.BASE_DIR) / 'static' / 'images' / 'demo' / filename, media / filename)
            Event.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'description': description,
                    'category': category,
                    'date': timezone.localdate() + timedelta(days=days),
                    'time': time(18 if i in (0, 1, 5, 7) else 14, 0),
                    'venue': venue,
                    'venue_address': venue + ', Main Campus',
                    'capacity': capacity,
                    'organizer': organizer,
                    'featured': i < 5,
                    'is_free': True,
                    'image': 'events/demo/' + filename,
                    'tags': category_name.lower() + ', campus, demo',
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                'Eight sample events are ready. Demo organizer: eventease_demo / EventDemo@123 (if newly created).'
            )
        )
