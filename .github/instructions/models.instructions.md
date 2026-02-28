---
description: 'Conventions and patterns for Django models in this project'
applyTo: '**/models.py,**/models/*.py'
---
# Model Conventions

## App Size

- Keep the number of models per app between 5 and 10. If an app exceeds ~20 models, break it into smaller, focused apps.

## Base Model

- Inherit from `TimeStampedModel` for any model that benefits from audit timestamps.
  `TimeStampedModel` adds `created` and `modified` fields automatically.
- Plain `models.Model` is used only when timestamps are not relevant (e.g., `Team`, `Match`).

```python
class MyModel(TimeStampedModel):
    ...
```

## Model Inheritance

Choose the right inheritance style deliberately:

| Style                  | When to use                                                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| No inheritance         | Models share only one or two fields — just repeat them.                                                                                         |
| Abstract base class    | Multiple models share enough fields that duplication becomes a maintenance burden. Table is only created for derived models.**Preferred.** |
| Proxy model            | Need a different Python-level behavior on the same table (e.g. custom manager, ordering). No new table.                                          |
| Multi-table (concrete) | **Avoid.** Creates implicit joins and hidden performance overhead on every query.                                                          |

> **Never use multi-table inheritance.** Use explicit `OneToOneField` or `ForeignKey` between models instead.

## Class-Level Constants

- Define status codes and choices as class-level string constants, not as separate enums or module-level variables.
- Group related constants into lists (e.g., `IN_PROGRESS_STATUS`, `FINISHED_STATUS`) for use in queries and conditionals.

```python
class Match(models.Model):
    NOT_STARTED = "NS"
    FINISHED = "FT"
    FINISHED_STATUS = [FINISHED, ...]
    STATUS_CHOICES = ((NOT_STARTED, "Não iniciada"), ...)
```

## Database Design

- **Start normalized.** No model should contain data already stored in another model. Use relationship fields liberally in the initial design.
- **Cache before denormalizing.** Set up caching in the right places before reaching for denormalization.
- **Denormalize only if absolutely needed.** Premature denormalization adds complexity and risks data loss. Only after caching options are exhausted.

## Fields

- Always provide a human-readable `verbose_name` as the first positional argument for fields displayed in forms or the admin (e.g., `models.DateTimeField("Data e hora")`).
- `data_source_id` maps to the external api-sports.io ID — never treat it as a Django `pk` or use it in internal relationships.
- Logo URLs for `Team` and `Competition` are constructed dynamically from `data_source_id`; there is no `logo` field.
- Use `models.UUIDField` for public-facing identifiers (e.g., `GuessPool.uuid`) to avoid exposing sequential PKs.
- Always define explicit `related_name` on `ForeignKey` and `ManyToManyField`.
- Use `on_delete=models.PROTECT` for FK relationships where accidental deletion would corrupt domain data.
- Never use `BinaryField` for file storage — store files in the filesystem and reference them with a `FileField`.

### When to Use `null` and `blank`

| Field type                                                                 | `null=True`                                                                                                     | `blank=True`                                                                                  |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `CharField`, `TextField`, `SlugField`, `EmailField`, `UUIDField` | Only when combined with `unique=True` and `blank=True` to avoid unique constraint violations on empty values. | When the form widget should accept empty input. Empty values are stored as `""`.              |
| `FileField`, `ImageField`                                              | Don't. Django stores a path string — follow the `CharField` pattern.                                           | When the form widget should accept empty input.                                                 |
| `BooleanField`                                                           | OK.                                                                                                               | Default is `blank=True`.                                                                      |
| `IntegerField`, `FloatField`, `DecimalField`, `DurationField`      | OK when `NULL` in the DB is meaningful.                                                                         | OK when the form widget should accept empty input (also set `null=True`).                     |
| `DateTimeField`, `DateField`, `TimeField`                            | OK when `NULL` in the DB is meaningful.                                                                         | OK for empty form widgets or when using `auto_now`/`auto_now_add` (also set `null=True`). |
| `ForeignKey`, `OneToOneField`                                          | OK when `NULL` in the DB is meaningful.                                                                         | OK for empty select widgets (also set `null=True`).                                           |
| `ManyToManyField`                                                        | No effect.                                                                                                        | OK for empty select widgets.                                                                    |
| `JSONField`                                                              | OK.                                                                                                               | OK.                                                                                             |

## Meta Class

Every model must define a `Meta` inner class with at least:

```python
class Meta:
    verbose_name = "..."
    verbose_name_plural = "..."
    ordering = (...)       # default queryset ordering
```

Add `unique_together` when composite uniqueness is required (e.g., `Match` on `home_team + away_team + date_time`).

## `__str__`

Always define `__str__`. Return a human-readable representation that identifies the object clearly in admin lists and logs.

## Business Logic in Models

Models are the canonical place for domain logic — keep logic out of views, forms and templates:

- Instance methods for operations on a single object (e.g., `match.is_finished()`, `pool.has_pending_match(guesser)`).
- Class methods for queryset-level operations (e.g., `Competition.get_with_matches_on_period(from_, to)`, `Match.get_happen_on_period(from_, to)`).
- Use `transaction.atomic()` inside methods that perform multiple related writes (e.g., `evaluate_and_consolidate_guesses`).

## `save()` Overrides

When overriding `save()`, detect create vs. update using `self.id is not None` **before** calling `super().save()` to avoid relying on stale state:

```python
def save(self, *args, **kwargs):
    is_update = self.id is not None
    super().save(*args, **kwargs)
    if is_update:
        ...
    else:
        ...
```

> **Warning:** Custom `save()` and `delete()` methods are **not** called when invoked via `RunPython` in migrations. Do not rely on model-level side effects during data migrations.

## Admin Display Helpers

Use `@admin.display` for computed fields shown in the Django admin. Always provide a `description` and `boolean=True` for boolean-valued methods:

```python
@admin.display(boolean=True, description="Aberta para palpites?")
def open_to_guesses(self) -> bool:
    ...
```

## Migrations

- Create migrations immediately whenever a new app or model is added (`python manage.py makemigrations`).
- Review the generated migration code before running it, especially for complex schema changes.
- Always back up data before running a migration in production.
- Verify that migrations can be rolled back before deploying.
- Use `RunPython.noop` as the `reverse_code` argument when a data migration is idempotent or has no meaningful reverse:

```python
migrations.RunPython(populate_data, migrations.RunPython.noop)
```

- Keep migration files in version control — they are as critical as the model code itself.

## Ranking Period Convention

`RankingEntry` and related methods encode time periods as `(year, month, week)` integers. A value of `0` means "all time" or "no constraint" for that dimension:

| year | month | week | Meaning                      |
| ---- | ----- | ---- | ---------------------------- |
| 0    | 0     | 0    | All time (overall)           |
| Y    | 0     | 0    | Annual (year Y)              |
| Y    | M     | 0    | Monthly (month M / year Y)   |
| Y    | 0     | W    | Weekly (ISO week W / year Y) |
