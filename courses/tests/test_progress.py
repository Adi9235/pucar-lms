"""R3 and R4: enrolment, lessons and progress tracking."""

from django.test import TestCase
from django.urls import reverse

from courses.models import Enrollment, LessonCompletion
from courses.services import enroll, mark_lesson_complete

from .helpers import make_course, make_instructor, make_user


def progress_of(enrollment):
    return Enrollment.objects.with_progress().get(pk=enrollment.pk).progress_percent


class ProgressCalculationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = make_instructor("teacher")
        cls.learner = make_user("learner")

    def test_four_of_seven_lessons_is_57_percent(self):
        course = make_course(self.instructor, lessons=7)
        enrollment, _ = enroll(self.learner, course)
        for lesson in course.lessons.all()[:4]:
            mark_lesson_complete(enrollment, lesson)

        self.assertEqual(progress_of(enrollment), 57)

    def test_course_without_lessons_is_zero_percent(self):
        enrollment, _ = enroll(self.learner, make_course(self.instructor))
        self.assertEqual(progress_of(enrollment), 0)

    def test_service_rejects_lesson_from_another_course(self):
        enrollment, _ = enroll(self.learner, make_course(self.instructor, "A", lessons=1))
        other_lesson = make_course(self.instructor, "B", lessons=1).lessons.get()

        with self.assertRaises(ValueError):
            mark_lesson_complete(enrollment, other_lesson)


class LearnerFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        instructor = make_instructor("teacher")
        cls.learner = make_user("learner")
        cls.course = make_course(instructor, "A", lessons=2)
        cls.first, cls.last = cls.course.lessons.all()
        cls.other_lesson = make_course(instructor, "B", lessons=1).lessons.get()

    def setUp(self):
        self.client.force_login(self.learner)

    def complete(self, lesson, course=None):
        url = reverse("courses:lesson_complete", args=[(course or self.course).pk, lesson.pk])
        return self.client.post(url)

    def test_enrol_then_course_appears_in_my_courses(self):
        response = self.client.post(reverse("courses:enrol", args=[self.course.pk]))

        self.assertRedirects(response, reverse("courses:detail", args=[self.course.pk]))
        my_courses = self.client.get(reverse("courses:my_courses"))
        self.assertContains(my_courses, "0 of 2 lessons done (0%)")

    def test_enrolling_twice_keeps_one_enrolment(self):
        self.client.post(reverse("courses:enrol", args=[self.course.pk]))
        self.client.post(reverse("courses:enrol", args=[self.course.pk]))
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_lesson_needs_enrolment(self):
        url = reverse("courses:lesson", args=[self.course.pk, self.first.pk])
        self.assertRedirects(self.client.get(url), reverse("courses:detail", args=[self.course.pk]))

        self.complete(self.first)
        self.assertFalse(LessonCompletion.objects.exists())

    def test_marking_complete_moves_to_next_lesson_then_back_to_course(self):
        enroll(self.learner, self.course)

        response = self.complete(self.first)
        self.assertRedirects(
            response, reverse("courses:lesson", args=[self.course.pk, self.last.pk])
        )
        response = self.complete(self.last)
        self.assertRedirects(response, reverse("courses:detail", args=[self.course.pk]))

    def test_marking_the_same_lesson_twice_records_it_once(self):
        enroll(self.learner, self.course)
        self.complete(self.first)
        self.complete(self.first)
        self.assertEqual(LessonCompletion.objects.count(), 1)

    def test_lesson_from_another_course_is_404(self):
        enroll(self.learner, self.course)
        self.assertEqual(self.complete(self.other_lesson).status_code, 404)
        self.assertFalse(LessonCompletion.objects.exists())
