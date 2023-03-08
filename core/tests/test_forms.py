from django.test import TestCase
from django.utils import timezone

from ..forms import RankingPeriodForm


class RankingPeriodFormTests(TestCase):
    def test_form_has_correct_fields(self):
        form = RankingPeriodForm()
        self.assertEquals(list(form.fields.keys()), ["ano", "mes"])

    def test_period_validation(self):
        form = RankingPeriodForm(data={"mes": "2", "ano": "2023"})
        self.assertTrue(form.is_valid())

        form = RankingPeriodForm(data={"mes": 5, "ano": 2022})
        self.assertTrue(form.is_valid())

        form = RankingPeriodForm(data={"mes": 0, "ano": 2022})
        self.assertTrue(form.is_valid())

        form = RankingPeriodForm(data={"mes": 1, "ano": 0})
        self.assertTrue(form.is_valid())
        self.assertDictEqual(form.cleaned_data, {"mes": "0", "ano": "0"})

        form = RankingPeriodForm(data={"mes": "foo", "ano": "2023"})
        self.assertFalse(form.is_valid())

        form = RankingPeriodForm(data={"mes": "2", "ano": "bar"})
        self.assertFalse(form.is_valid())

        form = RankingPeriodForm(data={"mes": "10", "ano": 2025})
        self.assertFalse(form.is_valid())

    def test_initial_values(self):
        current_date = timezone.now()
        initial_month = current_date.month
        initial_year = current_date.year
        form = RankingPeriodForm(
            initial={
                "mes": initial_month,
                "ano": initial_year,
            },
        )

        self.assertDictEqual(
            form.initial,
            {
                "mes": initial_month,
                "ano": initial_year,
            },
        )
