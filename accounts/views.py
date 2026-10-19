from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import CreateView

from .forms import SignUpForm


def home(request):
    """Send each user to the page for their role."""
    if request.user.is_instructor:
        return redirect("courses:teach_list")
    return redirect("courses:catalogue")


@method_decorator(login_not_required, name="dispatch")
class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "accounts/signup.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, f"Welcome, {user.username}. Your learner account is ready.")
        return redirect("home")


class LoginView(SuccessMessageMixin, auth_views.LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True
    success_message = "Welcome back, %(username)s."


class LogoutView(auth_views.LogoutView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have been logged out.")
        return response
