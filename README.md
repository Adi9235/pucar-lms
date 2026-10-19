# PUCAR LMS

A small learning management system for training legal-services staff, built with Django.
Instructors publish short courses made of ordered lessons and a multiple choice quiz.
Learners enrol, work through the lessons, mark them complete and take the quiz, which is marked
automatically. Admins manage everything through the Django admin.

Built with Django 5.2 LTS, server-rendered Django templates, Pico.css and SQLite.
There are no other dependencies.

## Requirements

- Python 3.10 or newer (tested on 3.13)
- git

## Setup

```bash
git clone <repo-url> pucar-lms
cd pucar-lms
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000 and log in with one of the demo accounts below.

`seed_demo` is safe to run again; it never creates duplicates.

## Demo accounts

| Username | Password | Role | What to try |
| --- | --- | --- | --- |
| `instructor1` | `Instructor@123` | Instructor | Owns "E-filing Basics" (published, with quiz) and "Handling Urgent Filings" (draft). Open Learner progress on E-filing Basics |
| `instructor2` | `Instructor@123` | Instructor | Owns "Courtroom Etiquette". Cannot open instructor1's courses |
| `learner1` | `Learner@123` | Learner | Enrolled in E-filing Basics, 3 of 5 lessons done, quiz attempts of 40% and 80% |
| `learner2` | `Learner@123` | Learner | Not enrolled anywhere: try the full enrol, read, complete and quiz flow |
| `admin` | `Admin@12345` | Superuser | Django admin at http://127.0.0.1:8000/admin/ |

The draft course is "Handling Urgent Filings" (`/courses/2/`). Learners get a 404 there, even
with the URL.

New sign-ups are always learners. To make someone an instructor, an admin edits their role in
the Django admin or uses the "Promote selected users to instructor" action.

## Running the tests

```bash
python manage.py test
```

Optional lint and format check, using the config in `pyproject.toml`:

```bash
pip install ruff
ruff check . && ruff format --check .
```

## Configuration

Settings read these environment variables. The defaults suit local development.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | an insecure development key | Set a real secret anywhere outside your laptop |
| `DJANGO_DEBUG` | `1` | Set to `0` to turn debug mode off |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated host names |

## Project structure

```
lms/         settings and root URLs
accounts/    custom User with a role, signup/login/logout, role mixins
courses/     courses, lessons, enrolment and progress; catalogue, instructor pages, dashboard
             querysets.py  reusable filters (published, owned_by, visible_to, with_progress)
             services.py   enrol and mark-complete
             mixins.py     course lookups that enforce ownership and visibility
             management/commands/seed_demo.py
quizzes/     quiz, questions, choices and attempts; authoring, taking and results
             services.py   grade_attempt(), the marking logic
templates/   base layout and one template per page
static/css/  a few styles on top of Pico.css
```

## Where each requirement lives

| Requirement | Main code | URLs |
| --- | --- | --- |
| R1 Accounts and roles | `accounts/models.py`, `accounts/forms.py`, `accounts/views.py` | `/accounts/signup/`, `/accounts/login/` |
| R2 Courses and lessons | `courses/views.py` (instructor section), `courses/forms.py` | `/teach/` |
| R3 Catalogue and enrolment | `CatalogueView`, `CourseDetailView`, `EnrolView`, `MyCoursesView` | `/courses/`, `/courses/mine/` |
| R4 Progress tracking | `EnrollmentQuerySet.with_progress()`, `CompleteLessonView` | `/courses/<id>/lessons/<id>/` |
| R5 Quizzes | `quizzes/forms.py`, `quizzes/services.py` (`grade_attempt`), `quizzes/views.py` | `/teach/<id>/quiz/`, `/courses/<id>/quiz/` |
| R6 Instructor dashboard | `CourseDashboardView`, `EnrollmentQuerySet.with_quiz_stats()` | `/teach/<id>/dashboard/` |
| R7 Permissions | `accounts/mixins.py`, `courses/mixins.py`, `LoginRequiredMiddleware` | all |
| R8 Django admin | `*/admin.py` | `/admin/` |
| R9 Tests | `*/tests/` | `python manage.py test` |

See [NOTES.md](NOTES.md) for the data model, design decisions and assumptions.
