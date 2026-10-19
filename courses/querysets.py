from django.db import models
from django.db.models import Count, Max, Q

PUBLISHED = "published"


class CourseQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=PUBLISHED)

    def owned_by(self, user):
        return self.filter(instructor=user)

    def visible_to(self, learner):
        """Published courses, plus any course this learner is already enrolled in."""
        return self.filter(Q(status=PUBLISHED) | Q(enrollments__learner=learner)).distinct()

    def with_counts(self):
        return self.annotate(
            lesson_count=Count("lessons", distinct=True),
            enrollment_count=Count("enrollments", distinct=True),
        )


class EnrollmentQuerySet(models.QuerySet):
    def with_progress(self):
        """Adds lessons_total and lessons_done, used by Enrollment.progress_percent."""
        return self.annotate(
            lessons_total=Count("course__lessons", distinct=True),
            lessons_done=Count("completions", distinct=True),
        )

    def with_quiz_stats(self):
        """Adds best_score (None if no attempts), attempt_count and passed_count."""
        return self.annotate(
            best_score=Max("quiz_attempts__score_percent"),
            attempt_count=Count("quiz_attempts", distinct=True),
            passed_count=Count(
                "quiz_attempts", filter=Q(quiz_attempts__passed=True), distinct=True
            ),
        )
