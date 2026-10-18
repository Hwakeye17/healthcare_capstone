
import unittest
from collections import Counter

from dataset import (
    CATEGORIES,
    REQUIRED_FIELDS,
    STATUSES,
    generate_appointments,
    validate_appointments,
)


class TestAppointmentDataset(unittest.TestCase):

    def setUp(self):
        self.appointments = generate_appointments(count=50, seed=42)

    def test_generates_at_least_40_records(self):
        self.assertGreaterEqual(len(self.appointments), 40)

    def test_every_record_has_exact_required_fields(self):
        for appointment in self.appointments:
            self.assertEqual(set(appointment.keys()), REQUIRED_FIELDS)

    def test_record_ids_are_unique(self):
        record_ids = [
            appointment["record_id"]
            for appointment in self.appointments
        ]
        self.assertEqual(len(record_ids), len(set(record_ids)))

    def test_all_categories_appear_at_least_three_times(self):
        counts = Counter(
            appointment["category"]
            for appointment in self.appointments
        )

        for category in CATEGORIES:
            self.assertGreaterEqual(counts[category], 3)

    def test_all_required_statuses_appear(self):
        counts = Counter(
            appointment["status"]
            for appointment in self.appointments
        )

        for status in STATUSES:
            self.assertGreaterEqual(counts[status], 1)

    def test_days_since_created_is_an_integer_between_zero_and_30(self):
        for appointment in self.appointments:
            days = appointment["days_since_created"]
            self.assertIs(type(days), int)
            self.assertGreaterEqual(days, 0)
            self.assertLessEqual(days, 30)

    def test_follow_up_required_is_a_boolean(self):
        for appointment in self.appointments:
            self.assertIs(
                type(appointment["follow_up_required"]),
                bool,
            )

    def test_follow_up_proportion_is_between_10_and_30_percent(self):
        follow_up_count = sum(
            appointment["follow_up_required"]
            for appointment in self.appointments
        )
        proportion = follow_up_count / len(self.appointments)

        self.assertGreaterEqual(proportion, 0.10)
        self.assertLessEqual(proportion, 0.30)

    def test_generation_is_reproducible(self):
        first = generate_appointments(count=50, seed=123)
        second = generate_appointments(count=50, seed=123)

        self.assertEqual(first, second)

    def test_different_seeds_can_generate_different_datasets(self):
        first = generate_appointments(count=50, seed=123)
        second = generate_appointments(count=50, seed=456)

        self.assertNotEqual(first, second)

    def test_rejects_fewer_than_40_records(self):
        with self.assertRaises(ValueError):
            generate_appointments(count=39)

    def test_validator_rejects_an_invalid_day_value(self):
        invalid = [dict(item) for item in self.appointments]
        invalid[0]["days_since_created"] = 31

        with self.assertRaises(ValueError):
            validate_appointments(invalid)

    def test_validator_rejects_extra_fields(self):
        invalid = [dict(item) for item in self.appointments]
        invalid[0]["patient_name"] = "Example"

        with self.assertRaises(ValueError):
            validate_appointments(invalid)


if __name__ == "__main__":
    unittest.main()
