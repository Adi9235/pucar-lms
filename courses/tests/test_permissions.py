"""R7: every permission rule, checked through real HTTP requests."""

from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Enrollment
from courses.services import enroll

from .helpers import make_course, make_instructor, make_quiz, make_user


class PermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_instructor("owner")
        cls.other_instructor = make_instructor("other")
        cls.learner = make_user("learner")
        cls.course = make_course(cls.owner, "Published", lessons=2)
        cls.draft = make_course(cls.owner, "Draft", status=Course.Status.DRAFT, lessons=1)
        make_quiz(cls.draft)
        cls.draft_lesson = cls.draft.lessons.get()

    def assert_status(self, user, method, url, status):
        self.client.force_login(user)
        response = getattr(self.client, method)(url)
        self.assertEqual(response.status_code, status, f"{method.upper()} {url}")

    # Login -------------------------------------------------------------------

    def test_anonymous_user_is_sent_to_login(self):
        url = reverse("courses:catalogue")
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    # Roles -------------------------------------------------------------------

    def test_learner_cannot_open_instructor_pages(self):
        for url in [
            reverse("courses:teach_list"),
            reverse("courses:course_create"),
            reverse("courses:course_manage", args=[self.course.pk]),
            reverse("courses:dashboard", args=[self.course.pk]),
            reverse("quizzes:quiz_edit", args=[self.course.pk]),
        ]:
            self.assert_status(self.learner, "get", url, 403)

    def test_learner_cannot_create_a_course(self):
        self.client.force_login(self.learner)
        response = self.client.post(
            reverse("courses:course_create"), {"title": "Hack", "status": "published"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Course.objects.filter(title="Hack").exists())

    def test_learner_cannot_edit_a_course(self):
        url = reverse("courses:course_update", args=[self.course.pk])
        self.assert_status(self.learner, "post", url, 403)

    def test_instructor_cannot_use_learner_pages(self):
        self.assert_status(self.owner, "get", reverse("courses:catalogue"), 403)
        self.assert_status(self.owner, "post", reverse("courses:enrol", args=[self.course.pk]), 403)
        self.assertFalse(Enrollment.objects.exists())

    # Ownership ---------------------------------------------------------------

    def test_instructor_cannot_edit_another_instructors_course(self):
        url = reverse("courses:course_update", args=[self.course.pk])
        self.assert_status(self.other_instructor, "get", url, 404)

        self.client.post(url, {"title": "Taken over", "status": "published"})
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "Published")

    def test_instructor_cannot_delete_another_instructors_course(self):
        url = reverse("courses:course_delete", args=[self.course.pk])
        self.assert_status(self.other_instructor, "post", url, 404)
        self.assertTrue(Course.objects.filter(pk=self.course.pk).exists())

    def test_instructor_cannot_touch_another_instructors_lessons_quiz_or_dashboard(self):
        lesson = self.course.lessons.first()
        for url in [
            reverse("courses:course_manage", args=[self.course.pk]),
            reverse("courses:lesson_update", args=[self.course.pk, lesson.pk]),
            reverse("courses:lesson_delete", args=[self.course.pk, lesson.pk]),
            reverse("courses:dashboard", args=[self.course.pk]),
            reverse("quizzes:quiz_edit", args=[self.draft.pk]),
            reverse("quizzes:question_create", args=[self.draft.pk]),
        ]:
            self.assert_status(self.other_instructor, "get", url, 404)

    # Drafts ------------------------------------------------------------------

    def test_draft_is_not_in_the_catalogue(self):
        self.client.force_login(self.learner)
        response = self.client.get(reverse("courses:catalogue"))
        self.assertEqual(list(response.context["courses"]), [self.course])

    def test_draft_urls_are_404_for_learner_who_is_not_enrolled(self):
        for url in [
            reverse("courses:detail", args=[self.draft.pk]),
            reverse("courses:lesson", args=[self.draft.pk, self.draft_lesson.pk]),
            reverse("quizzes:take", args=[self.draft.pk]),
        ]:
            self.assert_status(self.learner, "get", url, 404)

    def test_cannot_enrol_in_a_draft(self):
        self.assert_status(
            self.learner, "post", reverse("courses:enrol", args=[self.draft.pk]), 404
        )
        self.assertFalse(Enrollment.objects.exists())

    def test_enrolled_learner_keeps_access_when_course_goes_back_to_draft(self):
        enroll(self.learner, self.course)
        Course.objects.filter(pk=self.course.pk).update(status=Course.Status.DRAFT)
        lesson = self.course.lessons.first()

        self.assert_status(
            self.learner, "get", reverse("courses:detail", args=[self.course.pk]), 200
        )
        url = reverse("courses:lesson", args=[self.course.pk, lesson.pk])
        self.assert_status(self.learner, "get", url, 200)

    # Methods -----------------------------------------------------------------

    def test_state_changes_need_post(self):
        lesson = self.course.lessons.first()
        enroll(self.learner, self.course)
        for url in [
            reverse("courses:enrol", args=[self.course.pk]),
            reverse("courses:lesson_complete", args=[self.course.pk, lesson.pk]),
        ]:
            self.assert_status(self.learner, "get", url, 405)
