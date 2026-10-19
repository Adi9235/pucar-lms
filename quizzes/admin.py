from django.contrib import admin
from django.db.models import Count

from .forms import BaseChoiceFormSet
from .models import AttemptAnswer, Choice, Question, Quiz, QuizAttempt


class QuestionInline(admin.TabularInline):
    model = Question
    fields = ("order", "text")
    extra = 0
    show_change_link = True  # Choices are edited on the question page (admin cannot nest inlines).


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "pass_mark", "question_count")
    list_select_related = ("course",)
    search_fields = ("title", "course__title")
    inlines = (QuestionInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(question_count=Count("questions"))

    @admin.display(description="Questions", ordering="question_count")
    def question_count(self, obj):
        return obj.question_count


class ChoiceInline(admin.TabularInline):
    model = Choice
    formset = BaseChoiceFormSet  # same "exactly one correct" rule and safe save order as the app
    fields = ("text", "is_correct")
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "quiz", "order")
    list_filter = ("quiz",)
    list_select_related = ("quiz",)
    inlines = (ChoiceInline,)


class ReadOnlyMixin:
    """Attempts are records of what happened, so the admin can view but not change them."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class AttemptAnswerInline(ReadOnlyMixin, admin.TabularInline):
    model = AttemptAnswer
    fields = ("question", "selected_choice", "is_correct")
    extra = 0
    can_delete = False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = ("learner", "quiz", "score_percent", "passed", "submitted_at")
    list_filter = ("passed", "quiz")
    list_select_related = ("enrollment__learner", "quiz")
    inlines = (AttemptAnswerInline,)

    @admin.display(description="Learner", ordering="enrollment__learner__username")
    def learner(self, obj):
        return obj.enrollment.learner
