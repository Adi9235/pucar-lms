"""Small factories shared by the test suites of every app."""

from accounts.models import User
from courses.models import Course, Lesson
from quizzes.models import Choice, Question, Quiz

PASSWORD = "Test-pass-123"


def make_user(username, role=User.Role.LEARNER):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=PASSWORD, role=role
    )


def make_instructor(username):
    return make_user(username, role=User.Role.INSTRUCTOR)


def make_course(instructor, title="Course", status=Course.Status.PUBLISHED, lessons=0):
    course = Course.objects.create(instructor=instructor, title=title, status=status)
    for order in range(1, lessons + 1):
        Lesson.objects.create(course=course, title=f"Lesson {order}", content="Text", order=order)
    return course


def make_quiz(course, questions=5, pass_mark=70):
    """Each question gets one correct choice ("Right") and one wrong choice ("Wrong")."""
    quiz = Quiz.objects.create(course=course, title="Quiz", pass_mark=pass_mark)
    for order in range(1, questions + 1):
        question = Question.objects.create(quiz=quiz, text=f"Question {order}", order=order)
        Choice.objects.create(question=question, text="Right", is_correct=True)
        Choice.objects.create(question=question, text="Wrong", is_correct=False)
    return quiz


def answers_for(quiz, correct):
    """{question id: choice id} answering the first `correct` questions right, the rest wrong."""
    answers = {}
    for index, question in enumerate(quiz.questions.all()):
        answers[question.pk] = question.choices.get(is_correct=index < correct).pk
    return answers
