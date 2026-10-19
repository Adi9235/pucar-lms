"""R5 and R7 through the quiz pages: taking a quiz and viewing results."""

from django.test import TestCase
from django.urls import reverse

from courses.services import enroll
from courses.tests.helpers import answers_for, make_course, make_instructor, make_quiz, make_user
from quizzes.models import Quiz, QuizAttempt
from quizzes.services import grade_attempt


def form_data(answers):
    return {f"question_{question}": choice for question, choice in answers.items()}


class TakeQuizTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = make_instructor("teacher")
        cls.course = make_course(cls.instructor, lessons=1)
        cls.quiz = make_quiz(cls.course, questions=3)
        cls.learner = make_user("learner")
        cls.url = reverse("quizzes:take", args=[cls.course.pk])

    def setUp(self):
        self.client.force_login(self.learner)

    def test_learner_who_is_not_enrolled_cannot_take_the_quiz(self):
        detail = reverse("courses:detail", args=[self.course.pk])
        self.assertRedirects(self.client.get(self.url), detail)

        response = self.client.post(self.url, form_data(answers_for(self.quiz, 3)))
        self.assertRedirects(response, detail)
        self.assertFalse(QuizAttempt.objects.exists())

    def test_instructor_cannot_take_a_quiz(self):
        self.client.force_login(self.instructor)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_submitting_saves_an_attempt_and_shows_the_result(self):
        enroll(self.learner, self.course)

        response = self.client.post(self.url, form_data(answers_for(self.quiz, 3)))

        attempt = QuizAttempt.objects.get()
        self.assertRedirects(response, reverse("quizzes:attempt_result", args=[attempt.pk]))
        self.assertEqual((attempt.score_percent, attempt.passed), (100, True))

    def test_missing_answer_shows_an_error_and_saves_nothing(self):
        enroll(self.learner, self.course)
        data = form_data(answers_for(self.quiz, 3))
        data.popitem()

        response = self.client.post(self.url, data)

        self.assertContains(response, "Choose an answer.")
        self.assertFalse(QuizAttempt.objects.exists())

    def test_forged_choice_id_is_rejected(self):
        enroll(self.learner, self.course)
        answers = answers_for(self.quiz, 3)
        first, second = list(answers)[:2]
        answers[first] = answers[second]

        response = self.client.post(self.url, form_data(answers))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(QuizAttempt.objects.exists())

    def test_quiz_page_does_not_reveal_correct_answers(self):
        enroll(self.learner, self.course)
        response = self.client.get(self.url)
        self.assertNotContains(response, "is_correct")

    def test_quiz_without_questions_is_404(self):
        course = make_course(self.instructor, "Empty")
        Quiz.objects.create(course=course, title="Empty")
        enroll(self.learner, course)
        response = self.client.get(reverse("quizzes:take", args=[course.pk]))
        self.assertEqual(response.status_code, 404)


class AttemptResultTests(TestCase):
    def test_learner_cannot_see_someone_elses_result(self):
        course = make_course(make_instructor("teacher"))
        quiz = make_quiz(course)
        owner, other = make_user("owner"), make_user("other")
        enrollment, _ = enroll(owner, course)
        attempt = grade_attempt(enrollment, quiz, answers_for(quiz, 5))
        url = reverse("quizzes:attempt_result", args=[attempt.pk])

        self.client.force_login(owner)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 404)
