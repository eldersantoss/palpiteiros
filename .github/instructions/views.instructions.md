---
description: 'Conventions and patterns for Django views and view mixins in this project'
applyTo: '**/views.py,**/views/*.py,**/viewmixins.py,**/viewmixins/*.py'
---

# View Conventions

## Class-Based Views Only

- **Never use function-based views.** All views must be class-based (CBVs).
- Prefer Django's Generic Class-Based Views (GCBVs) from `django.views.generic` when they match the use case.
- Use `django.views.generic.View` for complex views that don't map cleanly to a single resource/action.

| View class       | When to use                                              |
| ---------------- | -------------------------------------------------------- |
| `TemplateView`   | Read-only display with no model or queryset involved     |
| `ListView`       | Display a list of objects                                |
| `DetailView`     | Display a single object                                  |
| `CreateView`     | Create a new model instance via a form                   |
| `UpdateView`     | Edit an existing model instance via a form               |
| `DeleteView`     | Delete a model instance                                  |
| `View`           | Multi-action views or anything that doesn't fit the above|

## Authentication

- Every view that requires a logged-in user **must** inherit `LoginRequiredMixin`.
- `LoginRequiredMixin` must always be the **first class in the inheritance list** (leftmost).

```python
class MyView(LoginRequiredMixin, generic.TemplateView):
    ...
```

## Mixin Order

Follow Python's MRO rules: base Django view class always goes **rightmost**; custom mixins go to the **left**:

```python
class MyPoolView(LoginRequiredMixin, GuessPoolMembershipMixin, generic.TemplateView):
    ...
```

- `LoginRequiredMixin` → leftmost
- Domain/custom mixins (e.g., `GuessPoolMembershipMixin`) → middle
- Django base view class → rightmost
- Mixins should not inherit from any other class (keep the chain simple).

## Authorization

- Use `GuessPoolMembershipMixin` (in `core/viewmixins.py`) for **all** pool-scoped views. Never re-implement membership checks inline.
- After `GuessPoolMembershipMixin.setup()` runs, `self.pool` and `self.guesser` are available on the view, and `self.pool.user_is_owner` / `self.pool.user_is_guesser` express the current user's role.
- For finer-grained authorization beyond membership (e.g., owner-only actions), override `dispatch()` and check the role before calling `super().dispatch()`:

```python
def dispatch(self, request, *args, **kwargs):
    if not self.pool.user_is_owner:
        return redirect_with_msg(
            self.request,
            "error",
            "Você não possui autorização pra realizar esta ação ❌",
        )
    return super().dispatch(request, *args, **kwargs)
```

> **Warning:** Any code placed before `super().dispatch()` runs even for unauthenticated users. Keep pre-super logic to authorization checks only.

## Redirects and User Feedback

- Use `redirect_with_msg` (from `core.helpers`) for all redirects that need to display a status message — never build redirect responses manually.
- Use `django.contrib.messages` for in-page feedback (success/error) on views that re-render the same template after a POST.
- Always pass a CSS extra tag as the third positional argument to `messages.success/error/warning` to control display duration:

```python
messages.success(self.request, "Palpites salvos ✅", "temp-msg short-time-msg")
```

## Presentation vs. Business Logic

- Views handle **presentation logic only**: choosing what to display, what form to render, and where to redirect.
- **Business logic belongs in models** (instance/class methods). Views should call model methods, not implement domain rules themselves.
- Queryset filtering that is view-specific can live in a `get_queryset()` method on the view; complex domain-level filtering belongs in the model.

## Context Data

- Add extra context in `get_context_data()`, always calling `super()` first:

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context["my_key"] = my_value
    return context
```

- `GuessPoolMembershipMixin` automatically injects `pool` and `guesser` into the context — do not duplicate them.

## Form Views

- Override `form_valid()` for custom logic after a form passes validation; it must return an `HttpResponseRedirect`.
- Override `form_invalid()` for custom logic when a form fails validation; it must return an `HttpResponse`.
- When a view needs custom widgets (e.g., `CheckboxSelectMultiple`), override `get_form_class()` using `modelform_factory`:

```python
def get_form_class(self):
    super().get_form_class()
    return modelform_factory(
        self.model,
        fields=self.fields,
        widgets={"competitions": CheckboxSelectMultiple()},
    )
```

## `GuessPoolMembershipMixin` — Writing New Pool-Scoped Mixins

When creating a new mixin that gates access based on pool membership:

- Set up state in `setup()`, never in `__init__()`.
- Perform authorization in `dispatch()` and redirect with `redirect_with_msg` if the check fails.
- Expose shared state as instance attributes so both the view and its templates can access them.
- Inject shared context in `get_context_data()` via `super()`.
- Keep the mixin free of model imports beyond what is strictly required for the gate check.
