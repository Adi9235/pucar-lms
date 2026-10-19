from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    """A staff member who is either an instructor or a learner.

    Admin access is Django's own is_staff / is_superuser and is separate from the role.
    """

    class Role(models.TextChoices):
        INSTRUCTOR = "instructor", "Instructor"
        LEARNER = "learner", "Learner"

    email = models.EmailField("email address")
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.LEARNER, db_index=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique_user_email_ci",
                violation_error_message="An account with this email already exists.",
            ),
        ]

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    @property
    def is_instructor(self):
        return self.role == self.Role.INSTRUCTOR

    @property
    def is_learner(self):
        return self.role == self.Role.LEARNER
