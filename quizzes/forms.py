from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Choice, Question, Quiz


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ("title", "pass_mark")


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ("text", "order")
        widgets = {"text": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, quiz, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.quiz = quiz
        if self.instance.pk is None:
            self.initial["order"] = Question.next_order(quiz)

    def clean_order(self):
        order = self.cleaned_data["order"]
        taken = Question.objects.filter(quiz=self.instance.quiz, order=order)
        if taken.exclude(pk=self.instance.pk).exists():
            raise ValidationError("Another question in this quiz already uses this position.")
        return order


class BaseChoiceFormSet(BaseInlineFormSet):
    """The answer choices for one question. Exactly one must be marked correct."""

    default_error_messages = {"too_few_forms": "Add at least %(num)d answer choices."}

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        # Blank extra rows have empty cleaned_data; rows ticked for deletion don't count.
        kept = [
            f.cleaned_data for f in self.forms if f.cleaned_data and not f.cleaned_data["DELETE"]
        ]
        if sum(1 for choice in kept if choice["is_correct"]) != 1:
            raise ValidationError("Mark exactly one choice as correct.")

    def save(self, commit=True):
        """Save wrong choices before the correct one.

        When the correct answer moves from choice A to choice B, saving B first would briefly
        give the question two correct choices and break the database constraint.
        """
        choices = super().save(commit=False)
        if commit:
            for choice in self.deleted_objects:
                choice.delete()
            for choice in sorted(choices, key=lambda choice: choice.is_correct):
                choice.save()
        return choices


ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    formset=BaseChoiceFormSet,
    fields=("text", "is_correct"),
    extra=2,
    min_num=2,
    validate_min=True,
    max_num=6,
    validate_max=True,
    can_delete=True,
    can_delete_extra=False,
)


class QuizTakeForm(forms.Form):
    """One radio group per question. Django rejects any choice that isn't in that group."""

    def __init__(self, *args, quiz, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = list(quiz.questions.prefetch_related("choices"))
        for question in self.questions:
            self.fields[f"question_{question.pk}"] = forms.TypedChoiceField(
                label=question.text,
                choices=[(choice.pk, choice.text) for choice in question.choices.all()],
                coerce=int,
                widget=forms.RadioSelect,
                error_messages={"required": "Choose an answer."},
            )

    def answers(self):
        """{question id: chosen choice id}, ready for grade_attempt()."""
        return {q.pk: self.cleaned_data[f"question_{q.pk}"] for q in self.questions}
