from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from neoskill.assessment.models import Question, QuestionOption
from neoskill.catalog.models import (
    Category,
    Course,
    Instructor,
    Lesson,
    Module,
    Practice,
    Topic,
    TopicTest,
)


class Command(BaseCommand):
    help = "Create an idempotent minimal catalog for local development."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        if settings.NEOSKILL_ENVIRONMENT == "production":
            raise CommandError("seed_dev is disabled in production.")

        category, _ = Category.objects.update_or_create(
            slug="dasturlash",
            defaults={"name": "Dasturlash"},
        )
        instructor, _ = Instructor.objects.update_or_create(
            slug="neo-ustoz",
            defaults={
                "name": "Neo Ustoz",
                "title": "Dasturlash bo‘yicha mentor",
                "bio": "NeoSkill development muhiti uchun namunaviy instructor.",
            },
        )
        course, _ = Course.objects.update_or_create(
            slug="python-asoslari",
            defaults={
                "category": category,
                "instructor": instructor,
                "title": "Python asoslari",
                "short_description": "Python dasturlash tiliga amaliy kirish.",
                "description": "NeoSkill development muhiti uchun minimal namunaviy kurs.",
                "level": Course.Level.BEGINNER,
                "language": "uz",
                "duration_minutes": 30,
                "is_free": True,
                "price": None,
                "status": Course.Status.DRAFT,
                "what_you_will_learn": ["Python sintaksisining asoslari"],
                "audience": ["Dasturlashni boshlayotganlar"],
                "requirements": ["Boshlang‘ich talab yo‘q"],
            },
        )
        module, _ = Module.objects.update_or_create(
            course=course,
            position=1,
            defaults={"title": "Kirish"},
        )
        topic, _ = Topic.objects.update_or_create(
            module=module,
            position=1,
            defaults={"title": "Birinchi qadam"},
        )
        Lesson.objects.update_or_create(
            topic=topic,
            position=1,
            defaults={
                "title": "Python bilan tanishuv",
                "kind": Lesson.Kind.TEXT,
                "content": "Python va NeoSkill kurs oqimi bilan tanishuv.",
                "duration_minutes": 10,
                "is_required": True,
                "free_preview": True,
            },
        )
        Practice.objects.update_or_create(
            topic=topic,
            defaults={
                "instructions": "Birinchi Python ifodangizni yozing.",
                "example": "print('Salom, NeoSkill!')",
                "is_required": False,
            },
        )
        topic_test, _ = TopicTest.objects.update_or_create(
            topic=topic,
            defaults={"passing_score": 70, "question_count": 1, "is_required": True},
        )
        question, _ = Question.objects.update_or_create(
            test=topic_test,
            position=1,
            defaults={"text": "Python faylining odatiy kengaytmasi qaysi?"},
        )
        question.options.update(is_correct=False)
        for position, text, is_correct in (
            (1, ".py", True),
            (2, ".js", False),
            (3, ".css", False),
            (4, ".sql", False),
        ):
            QuestionOption.objects.update_or_create(
                question=question,
                position=position,
                defaults={"text": text, "is_correct": is_correct},
            )

        self.stdout.write(self.style.SUCCESS("Development seed is ready (idempotent)."))
