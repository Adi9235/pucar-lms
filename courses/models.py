from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Max

from .querysets import PUBLISHED, CourseQuerySet, EnrollmentQuerySet


class Course(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = PUBLISHED, "Published"

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_taught",
        limit_choices_to={"role": "instructor"},
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CourseQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField()
    video_url = models.URLField("video link", blank=True)
    order = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], help_text="Position of the lesson in the course."
    )

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "order"], name="unique_lesson_order_per_course"
            ),
        ]

    def __str__(self):
        return f"{self.order}. {self.title}"

    @classmethod
    def next_order(cls, course):
        return (course.lessons.aggregate(Max("order"))["order__max"] or 0) + 1


class Enrollment(models.Model):
    learner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": "learner"},
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    objects = EnrollmentQuerySet.as_manager()

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(fields=["learner", "course"], name="unique_enrollment"),
        ]

    def __str__(self):
        return f"{self.learner} in {self.course}"

    @property
    def progress_percent(self):
        """Whole-number percentage, rounded down. Needs EnrollmentQuerySet.with_progress()."""
        if not self.lessons_total:
            return 0
        return 100 * self.lessons_done // self.lessons_total

    @property
    def has_passed(self):
        """True if any attempt passed. Needs EnrollmentQuerySet.with_quiz_stats()."""
        return self.passed_count > 0

    def completed_lesson_ids(self):
        return set(self.completions.values_list("lesson_id", flat=True))


class LessonCompletion(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="completions")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="completions")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "lesson"], name="unique_lesson_completion"
            ),
        ]

    def __str__(self):
        return f"{self.enrollment.learner} completed {self.lesson}"
