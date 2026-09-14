from collections.abc import Sequence
from uuid import UUID

from django.db import transaction
from django.db.models import F

from neoskill.assessment.models import Question


@transaction.atomic
def reorder_questions(test_id: UUID, ids: Sequence[UUID]) -> None:
    items = list(Question.objects.select_for_update().filter(test_id=test_id))
    by_id = {item.pk: item for item in items}
    if len(items) != len(ids) or set(by_id) != set(ids):
        raise ValueError("IDs must contain every question exactly once.")
    Question.objects.filter(test_id=test_id).update(position=F("position") + 1_000_000)
    for position, item_id in enumerate(ids, start=1):
        by_id[item_id].position = position
    Question.objects.bulk_update(items, ("position",))
