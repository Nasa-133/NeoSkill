from typing import Any

from django.db import transaction
from rest_framework import serializers

from neoskill.assessment.models import Question, QuestionOption, TestAttempt
from neoskill.catalog.serializers import AppendPositionMixin


class QuestionOptionSerializer(serializers.ModelSerializer[QuestionOption]):
    class Meta:
        model = QuestionOption
        fields = ("id", "text", "position", "is_correct")
        read_only_fields = ("id",)


class QuestionSerializer(AppendPositionMixin, serializers.ModelSerializer[Question]):
    options = QuestionOptionSerializer(many=True)
    position = serializers.IntegerField(min_value=1, required=False)
    parent_field = "test"

    class Meta:
        model = Question
        fields = ("id", "test", "text", "position", "options")
        read_only_fields = ("id",)

    def validate_options(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(value) != 4:
            raise serializers.ValidationError("A question requires exactly four options.")
        if {item["position"] for item in value} != {1, 2, 3, 4}:
            raise serializers.ValidationError("Option positions must be 1, 2, 3 and 4.")
        if sum(bool(item.get("is_correct")) for item in value) != 1:
            raise serializers.ValidationError("Exactly one option must be correct.")
        return value

    @transaction.atomic
    def create(self, validated_data: dict[str, Any]) -> Question:
        options = validated_data.pop("options")
        question = Question.objects.create(**validated_data)
        QuestionOption.objects.bulk_create(
            [QuestionOption(question=question, **item) for item in options]
        )
        return question

    @transaction.atomic
    def update(self, instance: Question, validated_data: dict[str, Any]) -> Question:
        options = validated_data.pop("options", None)
        for name, value in validated_data.items():
            setattr(instance, name, value)
        instance.save()
        if options is not None:
            instance.options.all().delete()
            QuestionOption.objects.bulk_create(
                [QuestionOption(question=instance, **item) for item in options]
            )
        return instance


class StudentQuestionOptionSerializer(serializers.ModelSerializer[QuestionOption]):
    class Meta:
        model = QuestionOption
        fields = ("id", "text", "position")


class StudentQuestionSerializer(serializers.ModelSerializer[Question]):
    options = StudentQuestionOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ("id", "text", "position", "options")


class TestAnswerSerializer(serializers.Serializer[dict[str, object]]):
    question_id = serializers.UUIDField()
    option_id = serializers.UUIDField()


class TestSubmissionSerializer(serializers.Serializer[dict[str, object]]):
    answers = TestAnswerSerializer(many=True)

    def validate_answers(self, value: list[dict[str, object]]) -> list[dict[str, object]]:
        if not 1 <= len(value) <= 500:
            raise serializers.ValidationError("Submit between 1 and 500 answers.")
        question_ids = [answer["question_id"] for answer in value]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError("Each question must be answered once.")
        return value


class TestAttemptListSerializer(serializers.ModelSerializer[TestAttempt]):
    class Meta:
        model = TestAttempt
        fields = ("id", "score", "result", "started_at", "completed_at")
