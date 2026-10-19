"""Database constraints on the course models."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from courses.models import Enrollment, Lesson

from .helpers import make_course, make_instructor, make_user


class CourseConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = make_instructor("teacher")
        cls.course = make_course(cls.instructor, "A", lessons=1)

    def test_learner_can_enrol_only_once(self):
        learner = make_user("learner")
        Enrollment.objects.create(learner=learner, course=self.course)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(learner=learner, course=self.course)

    def test_two_lessons_cannot_share_a_position(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Lesson.objects.create(course=self.course, title="Clash", content="x", order=1)

    def test_same_position_is_fine_in_another_course(self):
        other = make_course(self.instructor, "B")
        Lesson.objects.create(course=other, title="First", content="x", order=1)
        self.assertEqual(other.lessons.count(), 1)
