"""R5: automatic marking in grade_attempt()."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from courses.services import enroll
from courses.tests.helpers import answers_for, make_course, make_instructor, make_quiz, make_user
from quizzes.models import AttemptAnswer, Quiz, QuizAttempt
from quizzes.services import grade_attempt


class GradeAttemptTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = make_instructor("teacher")
        cls.course = make_course(cls.instructor)
        cls.quiz = make_quiz(cls.course, questions=5, pass_mark=70)
        cls.enrollment, _ = enroll(make_user("learner"), cls.course)

    def grade(self, correct, quiz=None):
        quiz = quiz or self.quiz
        return grade_attempt(self.enrollment, quiz, answers_for(quiz, correct))

    def test_all_correct_scores_100_and_passes(self):
        attempt = self.grade(correct=5)
        self.assertEqual((attempt.score_percent, attempt.passed), (100, True))

    def test_below_pass_mark_fails(self):
        attempt = self.grade(correct=3)
        self.assertEqual((attempt.score_percent, attempt.passed), (60, False))

    def test_score_equal_to_pass_mark_passes(self):
        Quiz.objects.filter(pk=self.quiz.pk).update(pass_mark=60)
        self.quiz.refresh_from_db()
        self.assertTrue(self.grade(correct=3).passed)

    def test_score_is_rounded_down_and_never_rounds_up_into_a_pass(self):
        quiz = make_quiz(make_course(self.instructor, "Three"), questions=3, pass_mark=67)
        self.enrollment, _ = enroll(self.enrollment.learner, quiz.course)

        attempt = self.grade(correct=2, quiz=quiz)  # 66.67%

        self.assertEqual((attempt.score_percent, attempt.passed), (66, False))

    def test_every_attempt_is_saved(self):
        self.grade(correct=1)
        self.grade(correct=5)
        self.assertEqual(self.enrollment.quiz_attempts.count(), 2)

    def test_each_answer_is_saved_with_whether_it_was_right(self):
        attempt = self.grade(correct=2)
        self.assertEqual(attempt.answers.count(), 5)
        self.assertEqual(attempt.answers.filter(is_correct=True).count(), 2)

    def test_choice_from_another_question_is_rejected(self):
        answers = answers_for(self.quiz, correct=5)
        first, second = list(answers)[:2]
        answers[first] = answers[second]

        with self.assertRaises(ValidationError):
            grade_attempt(self.enrollment, self.quiz, answers)
        self.assertFalse(QuizAttempt.objects.exists())

    def test_unanswered_question_is_rejected(self):
        answers = answers_for(self.quiz, correct=5)
        answers.popitem()

        with self.assertRaises(ValidationError):
            grade_attempt(self.enrollment, self.quiz, answers)
        self.assertFalse(AttemptAnswer.objects.exists())

    def test_quiz_from_another_course_is_rejected(self):
        other_quiz = make_quiz(make_course(self.instructor, "Other"))
        with self.assertRaises(ValueError):
            self.grade(correct=5, quiz=other_quiz)

    def test_quiz_without_questions_is_rejected(self):
        empty = Quiz.objects.create(course=make_course(self.instructor, "Empty"), title="Empty")
        self.enrollment, _ = enroll(self.enrollment.learner, empty.course)
        with self.assertRaises(ValueError):
            grade_attempt(self.enrollment, empty, {})
