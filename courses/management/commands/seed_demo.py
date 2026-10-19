"""Create demo users, courses, a quiz and some learner progress.

Safe to run more than once: existing rows are reused, never duplicated.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from courses.models import Course, Lesson
from courses.services import enroll, mark_lesson_complete
from quizzes.models import Choice, Question, Quiz, QuizAttempt
from quizzes.services import grade_attempt

USERS = [
    # username, password, role, is_superuser
    ("admin", "Admin@12345", User.Role.LEARNER, True),
    ("instructor1", "Instructor@123", User.Role.INSTRUCTOR, False),
    ("instructor2", "Instructor@123", User.Role.INSTRUCTOR, False),
    ("learner1", "Learner@123", User.Role.LEARNER, False),
    ("learner2", "Learner@123", User.Role.LEARNER, False),
]

EFILING_LESSONS = [
    (
        "What e-filing is and why the court uses it",
        "E-filing lets advocates and litigants submit case documents to the court online "
        "instead of on paper. Filings arrive in a single queue that clerks can review from "
        "any desk.\n\nFor court staff it means fewer lost papers, a clear record of when "
        "each document arrived, and faster handling of urgent matters.",
        "",
    ),
    (
        "Creating your account on the e-filing portal",
        "Every clerk has a personal account on the portal. Use your official email address "
        "and choose a strong password that you do not use anywhere else.\n\nAfter your first "
        "login, check that your name, designation and court are correct on your profile page.",
        "https://example.com/videos/efiling-account",
    ),
    (
        "Preparing documents: PDF format, file size and clear titles",
        "The portal accepts documents as PDF files. Scan pages straight, in the right order, "
        "and keep each file under the size limit shown on the upload page.\n\nGive every file "
        "a clear title, such as 'Written statement - Respondent 1', so the bench and other "
        "staff can find it quickly.",
        "",
    ),
    (
        "Submitting a filing and paying court fees online",
        "Before you submit, review every document and detail on the summary screen. Once "
        "submitted, a filing can no longer be edited.\n\nCourt fees are paid online at the end "
        "of the submission. Keep the payment receipt number with the filing record.",
        "",
    ),
    (
        "Tracking filing status and fixing returned filings",
        "The filing status page shows whether a filing is pending, accepted or returned with "
        "a defect.\n\nIf a filing is returned, read the defect note, correct the problem and "
        "resubmit the same filing. Do not start a new case for a defect.",
        "",
    ),
]

EFILING_QUIZ = [
    (
        "Which file format should documents be in before upload?",
        ["PDF", "Word document", "Photo of a printout", "Spreadsheet"],
    ),
    (
        "A filing is returned with a defect. What should you do?",
        ["Fix the defect and resubmit it", "Ignore it", "Start a new case", "Email the judge"],
    ),
    (
        "Where do you check whether a filing was accepted?",
        [
            "The filing status page on the portal",
            "The court notice board",
            "Your spam folder",
            "You cannot check",
        ],
    ),
    (
        "What should you do just before pressing Submit?",
        [
            "Review every document and detail",
            "Log out",
            "Clear your browser history",
            "Nothing, it can be edited later",
        ],
    ),
    (
        "Why give each uploaded document a clear title?",
        [
            "So court staff can identify it quickly",
            "It makes the file smaller",
            "The portal requires it to be in capitals",
            "It is not needed",
        ],
    ),
]  # The first choice of each question is the correct one.

URGENT_LESSONS = [
    (
        "What counts as an urgent filing",
        "Urgent filings include bail applications and stay requests that must reach the bench "
        "the same day.",
        "",
    ),
    (
        "Fast-tracking an urgent filing",
        "Mark the filing as urgent on the portal and inform the listing section by phone.",
        "",
    ),
]

ETIQUETTE_LESSONS = [
    (
        "Before the court sits",
        "Arrive early, check the cause list and keep case files in listing order.",
        "",
    ),
    (
        "During proceedings",
        "Keep phones silent, stand when the judge enters and speak only when addressed.",
        "",
    ),
    (
        "After the court rises",
        "Update the order sheet, return files to the record room and note the next dates.",
        "",
    ),
]


class Command(BaseCommand):
    help = "Create demo users, courses, a quiz and learner progress. Safe to run twice."

    @transaction.atomic
    def handle(self, *args, **options):
        users = {row[0]: self.upsert_user(*row) for row in USERS}

        efiling = self.upsert_course(
            users["instructor1"],
            "E-filing Basics for Court Clerks",
            "A short introduction to the court's e-filing portal: creating an account, "
            "preparing documents, submitting filings and handling returned filings.",
            Course.Status.PUBLISHED,
            EFILING_LESSONS,
        )
        self.upsert_course(
            users["instructor1"],
            "Handling Urgent Filings",
            "How to recognise and fast-track urgent matters. Still being written.",
            Course.Status.DRAFT,
            URGENT_LESSONS,
        )
        self.upsert_course(
            users["instructor2"],
            "Courtroom Etiquette for New Staff",
            "What is expected of court staff before, during and after proceedings.",
            Course.Status.PUBLISHED,
            ETIQUETTE_LESSONS,
        )
        quiz = self.upsert_quiz(efiling)
        self.add_learner_progress(users["learner1"], efiling, quiz)

        self.stdout.write(self.style.SUCCESS("Demo data ready. Log in with:"))
        for username, password, role, is_superuser in USERS:
            label = "admin" if is_superuser else role.label.lower()
            self.stdout.write(f"  {username:<12} {password:<15} {label}")

    def upsert_user(self, username, password, role, is_superuser):
        user, _ = User.objects.get_or_create(username=username)
        user.email = f"{username}@example.com"
        user.role = role
        user.is_staff = user.is_superuser = is_superuser
        user.set_password(password)
        user.save()
        return user

    def upsert_course(self, instructor, title, description, status, lessons):
        course, _ = Course.objects.update_or_create(
            title=title,
            defaults={"instructor": instructor, "description": description, "status": status},
        )
        for order, (lesson_title, content, video_url) in enumerate(lessons, start=1):
            Lesson.objects.update_or_create(
                course=course,
                order=order,
                defaults={"title": lesson_title, "content": content, "video_url": video_url},
            )
        return course

    def upsert_quiz(self, course):
        quiz, _ = Quiz.objects.update_or_create(
            course=course, defaults={"title": "E-filing Basics Quiz", "pass_mark": 70}
        )
        for order, (text, choices) in enumerate(EFILING_QUIZ, start=1):
            question, created = Question.objects.update_or_create(
                quiz=quiz, order=order, defaults={"text": text}
            )
            if created:
                Choice.objects.bulk_create(
                    Choice(question=question, text=choice, is_correct=index == 0)
                    for index, choice in enumerate(choices)
                )
        return quiz

    def add_learner_progress(self, learner, course, quiz):
        """learner1: 3 of 5 lessons done, one failed attempt (40%) then one pass (80%)."""
        enrollment, _ = enroll(learner, course)
        for lesson in course.lessons.all()[:3]:
            mark_lesson_complete(enrollment, lesson)

        if enrollment.quiz_attempts.exists():
            return
        questions = list(quiz.questions.prefetch_related("choices"))
        first = grade_attempt(enrollment, quiz, self.answers(questions, correct=2))
        grade_attempt(enrollment, quiz, self.answers(questions, correct=4))
        # Put the failed attempt a day earlier so the history reads in a natural order.
        QuizAttempt.objects.filter(pk=first.pk).update(
            submitted_at=timezone.now() - timedelta(days=1)
        )

    @staticmethod
    def answers(questions, correct):
        """Answer the first `correct` questions correctly and the rest wrongly."""
        result = {}
        for index, question in enumerate(questions):
            choices = list(question.choices.all())
            right = next(c for c in choices if c.is_correct)
            wrong = next(c for c in choices if not c.is_correct)
            result[question.pk] = (right if index < correct else wrong).pk
        return result
