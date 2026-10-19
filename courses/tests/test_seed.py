from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from courses.models import Course, Enrollment, Lesson, LessonCompletion
from quizzes.models import Choice, Question, QuizAttempt

MODELS = [User, Course, Lesson, Enrollment, LessonCompletion, Question, Choice, QuizAttempt]


class SeedDemoTests(TestCase):
    def test_running_twice_creates_nothing_new(self):
        call_command("seed_demo", stdout=StringIO())
        first = [model.objects.count() for model in MODELS]

        call_command("seed_demo", stdout=StringIO())

        self.assertEqual([model.objects.count() for model in MODELS], first)
        self.assertEqual(first, [5, 3, 10, 1, 3, 5, 20, 2])
