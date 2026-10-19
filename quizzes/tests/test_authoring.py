"""R5 for instructors: creating a quiz and editing questions with their choices."""

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from courses.services import enroll
from courses.tests.helpers import make_course, make_instructor, make_user
from quizzes.models import Choice, Question, Quiz, QuizAttempt


def question_data(choices, question=None, initial=0):
    """POST data for the question form plus its choice formset, as a browser sends it.

    `choices` is a list of dicts: {"text", "correct", "id", "delete"}.
    """
    data = {
        "text": "Which format?",
        "order": 1,
        "choices-TOTAL_FORMS": len(choices),
        "choices-INITIAL_FORMS": initial,
        "choices-MIN_NUM_FORMS": 0,
        "choices-MAX_NUM_FORMS": 1000,
    }
    for index, choice in enumerate(choices):
        data[f"choices-{index}-question"] = question.pk if question else ""
        data[f"choices-{index}-text"] = choice.get("text", "")
        if choice.get("correct"):
            data[f"choices-{index}-is_correct"] = "on"
        if choice.get("id"):
            data[f"choices-{index}-id"] = choice["id"]
        if choice.get("delete"):
            data[f"choices-{index}-DELETE"] = "on"
    return data


class QuizAuthoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = make_instructor("teacher")
        cls.course = make_course(cls.instructor)

    def setUp(self):
        self.client.force_login(self.instructor)

    def create_quiz(self):
        return Quiz.objects.create(course=self.course, title="Quiz")

    def post_new_question(self, choices):
        url = reverse("quizzes:question_create", args=[self.course.pk])
        return self.client.post(url, question_data(choices))

    def test_first_save_creates_the_quiz(self):
        url = reverse("quizzes:quiz_edit", args=[self.course.pk])
        self.client.post(url, {"title": "Final quiz", "pass_mark": 80})
        self.assertEqual(Quiz.objects.get(course=self.course).pass_mark, 80)

    def test_question_with_one_correct_choice_is_saved(self):
        self.create_quiz()

        response = self.post_new_question(
            [{"text": "PDF", "correct": True}, {"text": "Word"}, {}, {}]  # two blank rows
        )

        self.assertRedirects(response, reverse("courses:course_manage", args=[self.course.pk]))
        question = Question.objects.get()
        self.assertEqual(question.choices.count(), 2)
        self.assertEqual(question.choices.get(is_correct=True).text, "PDF")

    def test_question_needs_exactly_one_correct_choice(self):
        self.create_quiz()
        for choices in (
            [{"text": "PDF"}, {"text": "Word"}],
            [{"text": "PDF", "correct": True}, {"text": "Word", "correct": True}],
        ):
            response = self.post_new_question(choices)
            self.assertContains(response, "Mark exactly one choice as correct.")
        self.assertFalse(Question.objects.exists())

    def test_question_needs_at_least_two_choices(self):
        self.create_quiz()
        response = self.post_new_question([{"text": "PDF", "correct": True}, {}])
        self.assertContains(response, "Add at least 2 answer choices.")

    def test_moving_the_correct_answer_to_another_choice_saves(self):
        question = Question.objects.create(quiz=self.create_quiz(), text="Q", order=1)
        first = Choice.objects.create(question=question, text="A", is_correct=True)
        second = Choice.objects.create(question=question, text="B")
        url = reverse("quizzes:question_update", args=[self.course.pk, question.pk])

        for correct, other in ((second, first), (first, second)):
            data = question_data(
                [
                    {"text": "A", "id": first.pk, "correct": correct == first},
                    {"text": "B", "id": second.pk, "correct": correct == second},
                ],
                question=question,
                initial=2,
            )
            response = self.client.post(url, data)

            self.assertEqual(response.status_code, 302)
            correct.refresh_from_db()
            other.refresh_from_db()
            self.assertTrue(correct.is_correct)
            self.assertFalse(other.is_correct)


class QuizConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        course = make_course(make_instructor("teacher"))
        cls.quiz = Quiz.objects.create(course=course, title="Quiz")
        cls.question = Question.objects.create(quiz=cls.quiz, text="Q", order=1)

    def test_database_allows_only_one_correct_choice(self):
        Choice.objects.create(question=self.question, text="A", is_correct=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Choice.objects.create(question=self.question, text="B", is_correct=True)

    def test_pass_mark_must_be_between_0_and_100(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Quiz.objects.filter(pk=self.quiz.pk).update(pass_mark=150)

    def test_attempt_cannot_have_more_correct_answers_than_questions(self):
        enrollment, _ = enroll(make_user("learner"), self.quiz.course)
        with self.assertRaises(IntegrityError), transaction.atomic():
            QuizAttempt.objects.create(
                enrollment=enrollment,
                quiz=self.quiz,
                correct_count=6,
                total_questions=5,
                score_percent=100,
                passed=True,
            )
