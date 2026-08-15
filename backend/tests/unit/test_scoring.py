"""
Unit tests for the scoring engine (app.services.scoring.compute_points).

These tests import compute_points() directly — no HTTP client, no database,
no fixtures required (SRS NFR-4).

Coverage (SRS §11.1):
    - Each sport's conversion rate.
    - Flooring boundaries for km, seconds, and step counts.
    - Zero-value inputs → 0 points, not an error.
    - SRS §9.1 worked examples.
    - Unknown sport_type raises ValueError.
"""

import pytest

from app.services.scoring import compute_points


class TestRunning:
    def test_known_value(self):
        # floor(5.3 * 100) = 530
        assert compute_points("running", 5.3) == 530

    def test_exact_integer_km(self):
        assert compute_points("running", 10) == 1000

    def test_fractional_floors(self):
        # floor(1.009 * 100) = floor(100.9) = 100
        assert compute_points("running", 1.009) == 100

    def test_zero(self):
        assert compute_points("running", 0) == 0

    def test_sub_one_km(self):
        # floor(0.5 * 100) = 50
        assert compute_points("running", 0.5) == 50


class TestWalking:
    def test_srs_worked_example(self):
        """SRS §9.1: 1.55 km → floor(1.55 * 50) = 77"""
        assert compute_points("walking", 1.55) == 77

    def test_exact_km(self):
        assert compute_points("walking", 2) == 100

    def test_fractional_floors(self):
        # floor(1.019 * 50) = floor(50.95) = 50
        assert compute_points("walking", 1.019) == 50

    def test_zero(self):
        assert compute_points("walking", 0) == 0


class TestCycling:
    def test_known_value(self):
        # floor(10.0 * 25) = 250
        assert compute_points("cycling", 10.0) == 250

    def test_fractional_floors(self):
        # floor(1.039 * 25) = floor(25.975) = 25
        assert compute_points("cycling", 1.039) == 25

    def test_zero(self):
        assert compute_points("cycling", 0) == 0


class TestSwimming:
    def test_60s_boundary(self):
        """floor(60/60)*15 = 15"""
        assert compute_points("swimming", 60) == 15

    def test_59s_is_0_min(self):
        """SRS US-4: duration under 60 seconds → 0 points"""
        assert compute_points("swimming", 59) == 0

    def test_61s_is_1_min(self):
        """floor(61/60)*15 = 15"""
        assert compute_points("swimming", 61) == 15

    def test_119s_floors_to_1_min(self):
        """floor(119/60)*15 = 15"""
        assert compute_points("swimming", 119) == 15

    def test_120s_is_2_min(self):
        """floor(120/60)*15 = 30"""
        assert compute_points("swimming", 120) == 30

    def test_1855s_srs_example(self):
        """SRS §9.1 implicit: floor(1855/60)*15 = floor(30.916)*15 = 30*15 = 450"""
        assert compute_points("swimming", 1855) == 450

    def test_zero(self):
        assert compute_points("swimming", 0) == 0


class TestGym:
    def test_known_value(self):
        # floor(3600/60)*5 = 60*5 = 300
        assert compute_points("gym", 3600) == 300

    def test_60s_boundary(self):
        """floor(60/60)*5 = 5"""
        assert compute_points("gym", 60) == 5

    def test_59s_is_0_min(self):
        assert compute_points("gym", 59) == 0

    def test_61s_is_1_min(self):
        assert compute_points("gym", 61) == 5

    def test_115s_srs_example(self):
        """SRS §9.1: floor(115/60)=1 min → 1*5 = 5"""
        assert compute_points("gym", 115) == 5

    def test_zero(self):
        assert compute_points("gym", 0) == 0


class TestDailySteps:
    def test_100_steps(self):
        """floor(100/100) = 1"""
        assert compute_points("daily_steps", 100) == 1

    def test_99_steps(self):
        """floor(99/100) = 0"""
        assert compute_points("daily_steps", 99) == 0

    def test_199_steps(self):
        """floor(199/100) = 1"""
        assert compute_points("daily_steps", 199) == 1

    def test_200_steps(self):
        """floor(200/100) = 2"""
        assert compute_points("daily_steps", 200) == 2

    def test_399_steps(self):
        """SRS §9.1 worked example: floor(399/100) = 3"""
        assert compute_points("daily_steps", 399) == 3

    def test_8342_steps(self):
        """SRS §8 example: floor(8342/100) = 83"""
        assert compute_points("daily_steps", 8342) == 83

    def test_zero(self):
        assert compute_points("daily_steps", 0) == 0


class TestUnknownSport:
    def test_invalid_sport_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown sport_type"):
            compute_points("yoga", 30)

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            compute_points("", 10)
