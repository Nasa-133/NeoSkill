from collections.abc import Sequence
from uuid import UUID

from django.db import transaction
from django.db.models import F

from neoskill.catalog.models import Lesson, Module, Topic


@transaction.atomic
def reorder_modules(course_id: UUID, ids: Sequence[UUID]) -> None:
    items = list(Module.objects.select_for_update().filter(course_id=course_id))
    by_id = {item.pk: item for item in items}
    if len(items) != len(ids) or set(by_id) != set(ids):
        raise ValueError("IDs must contain every sibling exactly once.")
    Module.objects.filter(course_id=course_id).update(position=F("position") + 1_000_000)
    for position, item_id in enumerate(ids, start=1):
        by_id[item_id].position = position
    Module.objects.bulk_update(items, ("position",))


@transaction.atomic
def reorder_topics(module_id: UUID, ids: Sequence[UUID]) -> None:
    items = list(Topic.objects.select_for_update().filter(module_id=module_id))
    by_id = {item.pk: item for item in items}
    if len(items) != len(ids) or set(by_id) != set(ids):
        raise ValueError("IDs must contain every sibling exactly once.")
    Topic.objects.filter(module_id=module_id).update(position=F("position") + 1_000_000)
    for position, item_id in enumerate(ids, start=1):
        by_id[item_id].position = position
    Topic.objects.bulk_update(items, ("position",))


@transaction.atomic
def reorder_lessons(topic_id: UUID, ids: Sequence[UUID]) -> None:
    items = list(Lesson.objects.select_for_update().filter(topic_id=topic_id))
    by_id = {item.pk: item for item in items}
    if len(items) != len(ids) or set(by_id) != set(ids):
        raise ValueError("IDs must contain every sibling exactly once.")
    Lesson.objects.filter(topic_id=topic_id).update(position=F("position") + 1_000_000)
    for position, item_id in enumerate(ids, start=1):
        by_id[item_id].position = position
    Lesson.objects.bulk_update(items, ("position",))
