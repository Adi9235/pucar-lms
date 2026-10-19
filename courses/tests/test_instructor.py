"""R2 and R6: instructor course management and the progress dashboard."""

from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from courses.services import enroll, mark_lesson_complete
from quizzes.services import grade_attempt

from .helpers import answers_for, make_course, make_instructor, make_quiz, make_user


class CourseManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = make_instructor("teacher")

    def setUp(self):
        self.client.force_login(self.instructor)

    def test_new_course_belongs_to_instructor_and_starts_as_draft(self):
        response = self.client.post(
            reverse("courses:course_create"), {"title": "New", "status": "draft"}
        )

        course = Course.objects.get(title="New")
        self.assertEqual(course.instructor, self.instructor)
        self.assertFalse(course.is_published)
        self.assertRedirects(response, reverse("courses:course_manage", args=[course.pk]))

    def test_new_lesson_form_suggests_next_position(self):
        course = make_course(self.instructor, lessons=2)
        response = self.client.get(reverse("courses:lesson_create", args=[course.pk]))
        self.assertEqual(response.context["form"].initial["order"], 3)

    def test_lesson_position_already_taken_shows_an_error(self):
        course = make_course(self.instructor, lessons=1)
        response = self.client.post(
            reverse("courses:lesson_create", args=[course.pk]),
            {"title": "Clash", "content": "Text", "order": 1},
        )
        self.assertContains(response, "Another lesson in this course already uses this position.")
        self.assertEqual(course.lessons.count(), 1)

    def test_deleting_a_course_returns_to_course_list(self):
        course = make_course(self.instructor)
        response = self.client.post(reverse("courses:course_delete", args=[course.pk]))
        self.assertRedirects(response, reverse("courses:teach_list"))
        self.assertFalse(Course.objects.exists())


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = make_instructor("teacher")
        cls.course = make_course(cls.instructor, lessons=4)
        cls.quiz = make_quiz(cls.course, questions=5)

        cls.active = make_user("active")
        enrollment, _ = enroll(cls.active, cls.course)
        for lesson in cls.course.lessons.all()[:2]:
            mark_lesson_complete(enrollment, lesson)
        for correct in (2, 4, 3):  # 40%, 80%, 60%
            grade_attempt(enrollment, cls.quiz, answers_for(cls.quiz, correct))

        cls.new = make_user("newcomer")
        enroll(cls.new, cls.course)

    def test_dashboard_shows_lessons_done_and_best_score_per_learner(self):
        self.client.force_login(self.instructor)
        response = self.client.get(reverse("courses:dashboard", args=[self.course.pk]))

        rows = {e.learner.username: e for e in response.context["enrollments"]}
        self.assertEqual(rows["active"].lessons_done, 2)
        self.assertEqual(rows["active"].best_score, 80)
        self.assertTrue(rows["active"].has_passed)
        self.assertEqual(rows["active"].attempt_count, 3)
        self.assertIsNone(rows["newcomer"].best_score)
        self.assertEqual(rows["newcomer"].lessons_done, 0)
