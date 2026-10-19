"""Course lookups shared by the courses and quizzes views.

Each mixin fetches the course from the URL through a scoped queryset, so a course the
user may not see is a 404 rather than a 403: we never confirm that it exists.
"""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property

from accounts.mixins import InstructorRequiredMixin, LearnerRequiredMixin

from .models import Course, Enrollment


class InstructorCourseMixin(InstructorRequiredMixin):
    """Loads the course from the URL, limited to the logged-in instructor's own courses."""

    @cached_property
    def course(self):
        courses = Course.objects.owned_by(self.request.user)
        return get_object_or_404(courses, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        return super().get_context_data(course=self.course, **kwargs)

    def get_success_url(self):
        return reverse("courses:course_manage", args=[self.course.pk])


class OwnCourseMixin(InstructorCourseMixin):
    """For views whose object is the course itself."""

    def get_object(self, queryset=None):
        return self.course


class LearnerCourseMixin(LearnerRequiredMixin):
    """Loads the course if this learner may see it (published, or already enrolled)."""

    @cached_property
    def course(self):
        courses = Course.objects.visible_to(self.request.user)
        return get_object_or_404(courses, pk=self.kwargs["pk"])

    @cached_property
    def enrollment(self):
        enrollments = Enrollment.objects.with_progress()
        return enrollments.filter(learner=self.request.user, course=self.course).first()

    def get_context_data(self, **kwargs):
        return super().get_context_data(course=self.course, enrollment=self.enrollment, **kwargs)


class EnrolledLearnerMixin(LearnerCourseMixin):
    """The learner must also be enrolled. If not, send them to the course page to enrol.

    Users with the wrong role still get 403 from LearnerRequiredMixin.
    """

    def test_func(self):
        return super().test_func() and self.enrollment is not None

    def handle_no_permission(self):
        if self.request.user.is_learner:
            messages.error(self.request, "Enrol in this course to continue.")
            return redirect("courses:detail", pk=self.course.pk)
        return super().handle_no_permission()
