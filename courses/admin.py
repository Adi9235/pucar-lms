from django.contrib import admin

from .models import Course, Enrollment, Lesson, LessonCompletion


class LessonInline(admin.TabularInline):
    model = Lesson
    fields = ("order", "title", "video_url")
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "instructor",
        "status",
        "lesson_count",
        "enrollment_count",
        "created_at",
    )
    list_filter = ("status", "instructor")
    list_select_related = ("instructor",)
    search_fields = ("title",)
    inlines = (LessonInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).with_counts()

    @admin.display(description="Lessons", ordering="lesson_count")
    def lesson_count(self, obj):
        return obj.lesson_count

    @admin.display(description="Enrolments", ordering="enrollment_count")
    def enrollment_count(self, obj):
        return obj.enrollment_count


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    list_filter = ("course",)
    list_select_related = ("course",)
    search_fields = ("title",)


class LessonCompletionInline(admin.TabularInline):
    model = LessonCompletion
    fields = ("lesson", "completed_at")
    readonly_fields = ("lesson", "completed_at")
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("learner", "course", "enrolled_at")
    list_filter = ("course",)
    list_select_related = ("learner", "course")
    search_fields = ("learner__username", "course__title")
    inlines = (LessonCompletionInline,)


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "lesson", "completed_at")
    list_filter = ("lesson__course",)
    list_select_related = ("enrollment__learner", "enrollment__course", "lesson")
