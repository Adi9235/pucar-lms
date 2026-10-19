"""Role checks for class-based views. A user with the wrong role gets 403 Forbidden.

Login itself is enforced for every view by LoginRequiredMiddleware (see settings).
"""

from django.contrib.auth.mixins import UserPassesTestMixin


class InstructorRequiredMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_instructor


class LearnerRequiredMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_learner
