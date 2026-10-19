from django.contrib.admin.models import LogEntry
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from courses.tests.helpers import PASSWORD, make_instructor, make_user


class SignUpTests(TestCase):
    def sign_up(self, **overrides):
        data = {
            "username": "newbie",
            "email": "newbie@example.com",
            "password1": "Strong-pass-123",
            "password2": "Strong-pass-123",
            **overrides,
        }
        return self.client.post(reverse("accounts:signup"), data)

    def test_signup_and_login_pages_are_public(self):
        self.assertEqual(self.client.get(reverse("accounts:signup")).status_code, 200)
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200)

    def test_signup_creates_a_learner_and_logs_them_in(self):
        response = self.sign_up()

        user = User.objects.get(username="newbie")
        self.assertEqual(user.role, User.Role.LEARNER)
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_role_in_post_data_is_ignored(self):
        self.sign_up(role=User.Role.INSTRUCTOR, is_staff="on")

        user = User.objects.get(username="newbie")
        self.assertEqual(user.role, User.Role.LEARNER)
        self.assertFalse(user.is_staff)

    def test_email_is_stored_lowercased(self):
        self.sign_up(email="MixedCase@Example.COM")

        self.assertEqual(User.objects.get(username="newbie").email, "mixedcase@example.com")

    def test_same_email_in_different_case_is_rejected(self):
        make_user("existing")

        response = self.sign_up(email="EXISTING@Example.com")

        self.assertContains(response, "An account with this email already exists.")
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def test_logout_requires_post(self):
        self.client.force_login(make_user("learner"))

        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))


class EmailConstraintTests(TestCase):
    def test_database_rejects_same_email_in_different_case(self):
        User.objects.create_user("first", "same@example.com", PASSWORD)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user("second", "SAME@example.com", PASSWORD)


class HomeRedirectTests(TestCase):
    def test_learner_lands_on_catalogue(self):
        self.client.force_login(make_user("learner"))
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("courses:catalogue"))

    def test_instructor_lands_on_teaching_page(self):
        self.client.force_login(make_instructor("teacher"))
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("courses:teach_list"))


class PromoteActionTests(TestCase):
    def test_admin_action_promotes_learner_and_logs_it(self):
        admin = User.objects.create_superuser("boss", "boss@example.com", PASSWORD)
        learner = make_user("learner")
        self.client.force_login(admin)

        self.client.post(
            reverse("admin:accounts_user_changelist"),
            {"action": "promote_to_instructor", "_selected_action": [learner.pk]},
        )

        learner.refresh_from_db()
        self.assertEqual(learner.role, User.Role.INSTRUCTOR)
        self.assertTrue(LogEntry.objects.filter(object_id=str(learner.pk)).exists())
