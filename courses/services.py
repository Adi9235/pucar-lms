"""Write operations for learners. Views call these instead of creating rows directly."""

from .models import Enrollment, LessonCompletion


def enroll(learner, course):
    """Enrol a learner. Safe to call twice. The caller must fetch `course` via published()."""
    return Enrollment.objects.get_or_create(learner=learner, course=course)


def mark_lesson_complete(enrollment, lesson):
    """Record a completed lesson. Safe to call twice."""
    if lesson.course_id != enrollment.course_id:
        raise ValueError("Lesson does not belong to this course.")
    return LessonCompletion.objects.get_or_create(enrollment=enrollment, lesson=lesson)
