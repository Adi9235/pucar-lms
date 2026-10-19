# Notes

## Tools and AI used

- **Claude (Anthropic)**: analysing the brief, planning the data model and permissions,
  writing a build spec, then writing the code, templates, tests and these docs with me. I
  reviewed every file and can explain and change any of it.
- **Django's own tooling**: `startproject`, `startapp`, `makemigrations`.
- **ruff**: linting and formatting.
- **Playwright**: a throwaway script to click through every page and check the layout on
  desktop and phone widths. It is not part of the repo.

## Data model and why

```
User ──teaches──> Course ──> Lesson
  │                 │──> Quiz ──> Question ──> Choice
  └──enrols──> Enrollment ──> LessonCompletion (→ Lesson)
                    └──> QuizAttempt (→ Quiz) ──> AttemptAnswer (→ Question, Choice)
```

| Decision | Why |
| --- | --- |
| Custom `User(AbstractUser)` with a `role` field | Two roles, one field, no extra join, and Django recommends a custom user from the start. Admin access stays on Django's `is_staff` / `is_superuser`. Trade-off: one role per account |
| Email unique, ignoring case (`UniqueConstraint(Lower("email"))`), stored lowercased | One person cannot hold two accounts, and so cannot hold both roles |
| Signup has no role field | Least privilege: anyone can join as a learner, only an admin grants instructor. A forged `role=instructor` in the POST is ignored because the form only saves its listed fields |
| `Course.status` as TextChoices (`draft` / `published`) | Readable and easy to extend (for example `archived`) |
| `Lesson.order` with `UniqueConstraint(course, order)` | Explicit, stable ordering. New lessons get the next position, and the form explains a clash before the database would reject it |
| `Enrollment` with `UniqueConstraint(learner, course)` | One enrolment per learner per course. It is the anchor for everything a learner does |
| Progress and attempts hang off `Enrollment`, not `User` | "Must be enrolled" is built into the schema, and the dashboard is a single annotated query |
| Progress is computed, never stored | `with_progress()` counts lessons and completions in SQL, so it can't go stale when lessons are added or removed |
| `Quiz` is OneToOne with `Course` | The brief describes one quiz at the end. Several quizzes later means switching to a ForeignKey |
| `Choice` has a partial unique constraint (`question` where `is_correct`) | The database itself allows at most one correct answer. The choice formset makes it exactly one |
| `QuizAttempt` stores `correct_count`, `total_questions`, `score_percent`, `passed` | A snapshot of the result. Changing the pass mark or questions later does not rewrite history |
| `AttemptAnswer` stores each chosen answer | Lets the result page show what was right or wrong |
| `CheckConstraint`s on pass mark (0 to 100) and `correct_count <= total_questions` | Impossible values can't be saved, even outside the forms |
| `Course.instructor` uses `on_delete=PROTECT` | Deleting an instructor account can't silently delete their courses and learners' progress |

Two details worth knowing:

- **Changing the correct answer.** If an instructor moves the correct answer from choice A to
  choice B, saving B first would briefly give the question two correct choices and break the
  constraint. `BaseChoiceFormSet.save()` saves wrong choices first, then the correct one. The
  Django admin uses the same formset.
- **Score rounding.** Scores and progress are rounded down. With 2 of 3 correct (66.7%) the
  learner sees 66%, so a pass mark of 67% never looks reached when it wasn't.

## How permissions work

- `LoginRequiredMiddleware` protects every page. Only signup and login (and the admin's own login) are public.
- `InstructorRequiredMixin` / `LearnerRequiredMixin` return **403** for the wrong role.
- Course lookups go through scoped querysets and return **404** when the course isn't
  available to you: `owned_by(user)` for instructors, `visible_to(learner)` for learners,
  `published()` for enrolling. A 404 never confirms that a draft or someone else's course
  exists.
- Lessons and the quiz also need an enrolment. Without one, the learner is sent to the course
  page with a message, and nothing is saved.
- Every change is a POST with a CSRF token, including logout. GET on those URLs returns 405.
- The quiz page never includes which answer is correct. Lesson text is auto-escaped.

## Assumptions

- **Signup creates learners only.** Instructors are promoted by an admin.
- **Draft and enrolled learners.** A draft is hidden from the catalogue and from learners who
  aren't enrolled (404, even by URL), and nobody new can enrol. Learners already enrolled keep
  access if a published course goes back to draft. There is one live copy of each course, so
  edits show to them straight away.
- **Quiz access.** Any enrolled learner can take the quiz at any time. It isn't locked until
  the lessons are done.
- **Attempts.** Unlimited, and every attempt is saved. The dashboard shows the best score, and
  "passed" means passed at least once.
- **Pass mark.** Set per quiz, default 70%. Passed means score >= pass mark.
- **A quiz with no questions** is hidden from learners.
- **Instructors don't enrol** in courses; the learner pages return 403 for them.
- **Lessons** have a title, plain-text content and an optional video link (shown as a link,
  not embedded). No file uploads.
- **Sessions** use Django's defaults.

## What I left out, or would change with more time

- The stretch goals: REST API, lesson locking, certificates, search, CSV export, Malayalam
  translation, Docker and deployment, a full accessibility pass.
- Instructor invite links instead of admin promotion.
- A shorter, sliding session (a working day) for shared court-office computers.
- Drag-and-drop reordering of lessons and questions instead of typing positions.

## Time spent

About 3 hours.
