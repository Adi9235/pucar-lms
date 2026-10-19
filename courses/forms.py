from django import forms
from django.core.exceptions import ValidationError

from .models import Course, Lesson


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ("title", "description", "status")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "status": forms.RadioSelect,
        }
        help_texts = {
            "status": "Draft courses are hidden from learners who are not already enrolled.",
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ("title", "content", "video_url", "order")
        widgets = {"content": forms.Textarea(attrs={"rows": 12})}
        help_texts = {"content": "Plain text. Blank lines start new paragraphs."}

    def __init__(self, *args, course, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.course = course
        if self.instance.pk is None:
            self.initial["order"] = Lesson.next_order(course)

    def clean_order(self):
        order = self.cleaned_data["order"]
        taken = Lesson.objects.filter(course=self.instance.course, order=order)
        if taken.exclude(pk=self.instance.pk).exists():
            raise ValidationError("Another lesson in this course already uses this position.")
        return order
