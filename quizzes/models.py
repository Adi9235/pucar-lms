from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Max, Q

from courses.models import Course, Enrollment


class Quiz(models.Model):
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=200)
    pass_mark = models.PositiveSmallIntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage needed to pass.",
    )

    class Meta:
        verbose_name_plural = "quizzes"
        constraints = [
            models.CheckConstraint(
                condition=Q(pass_mark__gte=0) & Q(pass_mark__lte=100),
                name="quiz_pass_mark_0_100",
            ),
        ]

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], help_text="Position of the question in the quiz."
    )

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "order"], name="unique_question_order_per_quiz"
            ),
        ]

    def __str__(self):
        return self.text

    @classmethod
    def next_order(cls, quiz):
        return (quiz.questions.aggregate(Max("order"))["order__max"] or 0) + 1


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField("correct", default=False)

    class Meta:
        ordering = ["id"]
        constraints = [
            # A partial unique index: at most one row per question may have is_correct=True.
            models.UniqueConstraint(
                fields=["question"],
                condition=Q(is_correct=True),
                name="one_correct_choice_per_question",
            ),
        ]

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    """One submitted attempt. The score is a snapshot and is never recalculated."""

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    correct_count = models.PositiveSmallIntegerField()
    total_questions = models.PositiveSmallIntegerField()
    score_percent = models.PositiveSmallIntegerField(help_text="0 to 100, rounded down.")
    passed = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(correct_count__lte=F("total_questions")),
                name="attempt_correct_lte_total",
            ),
        ]

    def __str__(self):
        return f"{self.enrollment.learner}: {self.score_percent}% on {self.quiz}"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="+")
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name="+")
    is_correct = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"], name="unique_answer_per_question"
            ),
        ]

    def __str__(self):
        return f"{self.question}: {self.selected_choice}"
