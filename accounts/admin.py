from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    fieldsets = (*DjangoUserAdmin.fieldsets, ("Role", {"fields": ("role",)}))
    add_fieldsets = (*DjangoUserAdmin.add_fieldsets, ("Profile", {"fields": ("email", "role")}))
    actions = ("promote_to_instructor", "demote_to_learner")

    @admin.action(description="Promote selected users to instructor")
    def promote_to_instructor(self, request, queryset):
        self._set_role(request, queryset, User.Role.INSTRUCTOR)

    @admin.action(description="Change selected users to learner")
    def demote_to_learner(self, request, queryset):
        self._set_role(request, queryset, User.Role.LEARNER)

    def _set_role(self, request, queryset, role):
        users = list(queryset.exclude(role=role))
        for user in users:
            user.role = role
            user.save(update_fields=["role"])
            # Recorded in the admin history, so there is an audit trail of role changes.
            self.log_change(request, user, f"Changed role to {user.get_role_display()}.")
        self.message_user(
            request, f"{len(users)} user(s) changed to {role.label}.", messages.SUCCESS
        )
