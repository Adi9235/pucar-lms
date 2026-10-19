from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.functional import cached_property
from django.views.generic import DeleteView, DetailView, FormView, TemplateView, UpdateView

from accounts.mixins import LearnerRequiredMixin
from courses.mixins import EnrolledLearnerMixin, InstructorCourseMixin

from .forms import ChoiceFormSet, QuestionForm, QuizForm, QuizTakeForm
from .models import Question, Quiz, QuizAttempt
from .services import grade_attempt

# ---------------------------------------------------------------------------
# Instructor: quiz settings and questions
# ---------------------------------------------------------------------------


class QuizEditView(InstructorCourseMixin, SuccessMessageMixin, UpdateView):
    """Creates the course's quiz on first save, and edits it afterwards."""

    form_class = QuizForm
    template_name = "quizzes/quiz_form.html"
    success_message = "Quiz settings saved."

    def get_object(self, queryset=None):
        quiz = Quiz.objects.filter(course=self.course).first()
        return quiz or Quiz(course=self.course, title=f"{self.course.title} quiz")


class QuestionCreateView(InstructorCourseMixin, TemplateView):
    """A question and its answer choices, edited together on one page."""

    template_name = "quizzes/question_form.html"

    @cached_property
    def quiz(self):
        return get_object_or_404(Quiz, course=self.course)

    def get_question(self):
        return None

    def get(self, request, *args, **kwargs):
        form = QuestionForm(instance=self.get_question(), quiz=self.quiz)
        return self.render_forms(form, ChoiceFormSet(instance=form.instance))

    def post(self, request, *args, **kwargs):
        form = QuestionForm(request.POST, instance=self.get_question(), quiz=self.quiz)
        formset = ChoiceFormSet(request.POST, instance=form.instance)
        if all([form.is_valid(), formset.is_valid()]):
            with transaction.atomic():
                form.save()
                formset.save()
            messages.success(request, "Question saved.")
            return redirect(self.get_success_url())
        return self.render_forms(form, formset)

    def render_forms(self, form, formset):
        context = self.get_context_data(form=form, formset=formset, quiz=self.quiz)
        return self.render_to_response(context)


class QuestionUpdateView(QuestionCreateView):
    def get_question(self):
        return get_object_or_404(self.quiz.questions, pk=self.kwargs["question_pk"])


class QuestionDeleteView(InstructorCourseMixin, SuccessMessageMixin, DeleteView):
    template_name = "confirm_delete.html"
    pk_url_kwarg = "question_pk"
    success_message = "Question deleted."

    def get_queryset(self):
        return Question.objects.filter(quiz__course=self.course)


# ---------------------------------------------------------------------------
# Learner: take the quiz and review results
# ---------------------------------------------------------------------------


class QuizTakeView(EnrolledLearnerMixin, FormView):
    form_class = QuizTakeForm
    template_name = "quizzes/quiz_take.html"

    @cached_property
    def quiz(self):
        quiz = get_object_or_404(Quiz, course=self.course)
        if not quiz.questions.exists():
            raise Http404("This quiz has no questions yet.")
        return quiz

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "quiz": self.quiz}

    def get_context_data(self, **kwargs):
        return super().get_context_data(quiz=self.quiz, **kwargs)

    def form_valid(self, form):
        try:
            attempt = grade_attempt(self.enrollment, self.quiz, form.answers())
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)

        if attempt.passed:
            messages.success(self.request, f"You scored {attempt.score_percent}%. You passed!")
        else:
            messages.warning(
                self.request,
                f"You scored {attempt.score_percent}%. The pass mark is {self.quiz.pass_mark}%.",
            )
        return redirect("quizzes:attempt_result", pk=attempt.pk)


class AttemptResultView(LearnerRequiredMixin, DetailView):
    template_name = "quizzes/attempt_result.html"
    context_object_name = "attempt"

    def get_queryset(self):
        # Only the learner's own attempts; anyone else's is a 404.
        return (
            QuizAttempt.objects.filter(enrollment__learner=self.request.user)
            .select_related("quiz", "enrollment__course")
            .prefetch_related("answers__question", "answers__selected_choice")
        )
