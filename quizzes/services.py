from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AttemptAnswer, QuizAttempt


def grade_attempt(enrollment, quiz, answers):
    """Mark a submitted quiz and save the attempt together with every answer.

    `answers` maps question id -> chosen choice id. Every question must be answered with one
    of its own choices, otherwise ValidationError is raised and nothing is saved.

    The score is rounded down, so the percentage shown can never look like a pass that was
    not reached. The learner passes when score >= pass mark.
    """
    if quiz.course_id != enrollment.course_id:
        raise ValueError("This quiz belongs to a different course.")

    questions = list(quiz.questions.prefetch_related("choices"))
    if not questions:
        raise ValueError("This quiz has no questions.")

    selected = []
    for question in questions:
        choices = {choice.pk: choice for choice in question.choices.all()}
        choice = choices.get(answers.get(question.pk))
        if choice is None:
            raise ValidationError(f"Choose one of the answers for: {question.text}")
        selected.append((question, choice))

    correct_count = sum(choice.is_correct for _, choice in selected)
    total = len(questions)
    score = 100 * correct_count // total

    with transaction.atomic():
        attempt = QuizAttempt.objects.create(
            enrollment=enrollment,
            quiz=quiz,
            correct_count=correct_count,
            total_questions=total,
            score_percent=score,
            passed=score >= quiz.pass_mark,
        )
        AttemptAnswer.objects.bulk_create(
            AttemptAnswer(
                attempt=attempt,
                question=question,
                selected_choice=choice,
                is_correct=choice.is_correct,
            )
            for question, choice in selected
        )
    return attempt
