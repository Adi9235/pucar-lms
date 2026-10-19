from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import InstructorRequiredMixin, LearnerRequiredMixin
from quizzes.models import Quiz

from .forms import CourseForm, LessonForm
from .mixins import EnrolledLearnerMixin, InstructorCourseMixin, LearnerCourseMixin, OwnCourseMixin
from .models import Course, Lesson
from .services import enroll, mark_lesson_complete

# ---------------------------------------------------------------------------
# Learner pages
# ---------------------------------------------------------------------------


class CatalogueView(LearnerRequiredMixin, ListView):
    template_name = "courses/catalogue.html"
    context_object_name = "courses"

    def get_queryset(self):
        return (
            Course.objects.published().with_counts().select_related("instructor").order_by("title")
        )

    def get_context_data(self, **kwargs):
        enrolled_ids = set(self.request.user.enrollments.values_list("course_id", flat=True))
        return super().get_context_data(enrolled_ids=enrolled_ids, **kwargs)


class MyCoursesView(LearnerRequiredMixin, ListView):
    template_name = "courses/my_courses.html"
    context_object_name = "enrollments"

    def get_queryset(self):
        return (
            self.request.user.enrollments.with_progress()
            .with_quiz_stats()
            .select_related("course__quiz")
        )


class CourseDetailView(LearnerCourseMixin, DetailView):
    template_name = "courses/course_detail.html"

    def get_object(self, queryset=None):
        return self.course

    def get_context_data(self, **kwargs):
        # Only offer the quiz once it has at least one question.
        quiz = (
            Quiz.objects.filter(course=self.course)
            .annotate(question_count=Count("questions"))
            .filter(question_count__gt=0)
            .first()
        )
        enrollment = self.enrollment
        return super().get_context_data(
            lessons=self.course.lessons.all(),
            completed_ids=enrollment.completed_lesson_ids() if enrollment else set(),
            quiz=quiz,
            attempts=enrollment.quiz_attempts.all() if enrollment else [],
            **kwargs,
        )


class EnrolView(LearnerRequiredMixin, View):
    def post(self, request, pk):
        course = get_object_or_404(Course.objects.published(), pk=pk)
        _, created = enroll(request.user, course)
        if created:
            messages.success(request, f"You're enrolled in “{course.title}”.")
        else:
            messages.info(request, "You're already enrolled in this course.")
        return redirect("courses:detail", pk=course.pk)


class LessonDetailView(EnrolledLearnerMixin, DetailView):
    template_name = "courses/lesson_detail.html"
    context_object_name = "lesson"
    pk_url_kwarg = "lesson_pk"

    def get_queryset(self):
        return self.course.lessons.all()

    def get_context_data(self, **kwargs):
        lesson = self.object
        lessons = self.course.lessons.all()
        return super().get_context_data(
            is_completed=self.enrollment.completions.filter(lesson=lesson).exists(),
            previous_lesson=lessons.filter(order__lt=lesson.order).last(),
            next_lesson=lessons.filter(order__gt=lesson.order).first(),
            **kwargs,
        )


class CompleteLessonView(EnrolledLearnerMixin, View):
    def post(self, request, pk, lesson_pk):
        lesson = get_object_or_404(self.course.lessons, pk=lesson_pk)
        _, created = mark_lesson_complete(self.enrollment, lesson)
        if created:
            messages.success(request, f"“{lesson.title}” marked complete.")
        next_lesson = self.course.lessons.filter(order__gt=lesson.order).first()
        if next_lesson:
            return redirect("courses:lesson", pk=self.course.pk, lesson_pk=next_lesson.pk)
        return redirect("courses:detail", pk=self.course.pk)


# ---------------------------------------------------------------------------
# Instructor pages
# ---------------------------------------------------------------------------


class TeachCourseListView(InstructorRequiredMixin, ListView):
    template_name = "courses/teach_list.html"
    context_object_name = "courses"

    def get_queryset(self):
        return Course.objects.owned_by(self.request.user).with_counts()


class CourseCreateView(InstructorRequiredMixin, SuccessMessageMixin, CreateView):
    model = Course
    form_class = CourseForm
    success_message = "Course “%(title)s” created. Add your first lesson next."

    def form_valid(self, form):
        form.instance.instructor = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("courses:course_manage", args=[self.object.pk])


class CourseManageView(OwnCourseMixin, DetailView):
    template_name = "courses/course_manage.html"

    def get_context_data(self, **kwargs):
        quiz = Quiz.objects.filter(course=self.course).prefetch_related("questions__choices")
        return super().get_context_data(
            lessons=self.course.lessons.all(),
            quiz=quiz.first(),
            enrollment_count=self.course.enrollments.count(),
            **kwargs,
        )


class CourseUpdateView(OwnCourseMixin, SuccessMessageMixin, UpdateView):
    form_class = CourseForm
    success_message = "Course saved."


class CourseDeleteView(OwnCourseMixin, SuccessMessageMixin, DeleteView):
    template_name = "confirm_delete.html"

    def get_success_url(self):
        return reverse("courses:teach_list")

    def get_success_message(self, cleaned_data):
        return f"Course “{self.object.title}” deleted."


class CourseDashboardView(InstructorCourseMixin, TemplateView):
    """R6: every enrolled learner with lessons done and best quiz score, in one query."""

    template_name = "courses/dashboard.html"

    def get_context_data(self, **kwargs):
        enrollments = (
            self.course.enrollments.with_progress()
            .with_quiz_stats()
            .select_related("learner")
            .order_by("learner__username")
        )
        return super().get_context_data(enrollments=enrollments, **kwargs)


class LessonMixin(InstructorCourseMixin):
    model = Lesson
    pk_url_kwarg = "lesson_pk"

    def get_queryset(self):
        return self.course.lessons.all()


class LessonFormMixin(LessonMixin, SuccessMessageMixin):
    form_class = LessonForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "course": self.course}


class LessonCreateView(LessonFormMixin, CreateView):
    success_message = "Lesson “%(title)s” added."


class LessonUpdateView(LessonFormMixin, UpdateView):
    success_message = "Lesson “%(title)s” saved."


class LessonDeleteView(LessonMixin, SuccessMessageMixin, DeleteView):
    template_name = "confirm_delete.html"

    def get_success_message(self, cleaned_data):
        return f"Lesson “{self.object.title}” deleted."
