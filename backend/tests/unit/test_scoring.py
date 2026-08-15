"""
Unit tests for the scoring engine (app.services.scoring).

These tests import compute_points() directly — no HTTP client, no database,
no fixtures required (SRS NFR-4).

Coverage required by SRS §11.1:
    - Each sport's conversion rate against a known input/output pair.
    - Flooring boundaries:
        km  : exact values, fractional values
        sec : 60s, 119s, 120s boundaries
        steps: 100, 199, 200, 399 boundaries
    - Zero-value inputs → 0 points, not an error.
    - SRS worked examples: 1.55 km walking → 77; 1:55 → floors to 1 min; 399 steps → 3.
"""

import pytest

# from app.services.scoring import compute_points  # uncomment when implemented


class TestRunning:
    def test_known_value(self):
        pytest.skip("not yet implemented")

    def test_fractional_floors(self):
        pytest.skip("not yet implemented")

    def test_zero(self):
        pytest.skip("not yet implemented")


class TestWalking:
    def test_srs_worked_example(self):
        """SRS §9.1: 1.55 km → floor(1.55 * 50) = 77"""
        pytest.skip("not yet implemented")

    def test_zero(self):
        pytest.skip("not yet implemented")


class TestCycling:
    def test_known_value(self):
        pytest.skip("not yet implemented")

    def test_zero(self):
        pytest.skip("not yet implemented")


class TestSwimming:
    def test_60s_boundary(self):
        """floor(60/60)*15 = 15"""
        pytest.skip("not yet implemented")

    def test_119s_floors_to_1_min(self):
        """floor(119/60)*15 = 15"""
        pytest.skip("not yet implemented")

    def test_120s_is_2_min(self):
        """floor(120/60)*15 = 30"""
        pytest.skip("not yet implemented")

    def test_55s_is_0_min(self):
        """SRS US-4: durationSec under 60 → 0 points"""
        pytest.skip("not yet implemented")

    def test_zero(self):
        pytest.skip("not yet implemented")


class TestGym:
    def test_known_value(self):
        pytest.skip("not yet implemented")

    def test_zero(self):
        pytest.skip("not yet implemented")


class TestDailySteps:
    def test_100_steps(self):
        """floor(100/100) = 1"""
        pytest.skip("not yet implemented")

    def test_199_steps(self):
        """floor(199/100) = 1"""
        pytest.skip("not yet implemented")

    def test_200_steps(self):
        """floor(200/100) = 2"""
        pytest.skip("not yet implemented")

    def test_399_steps(self):
        """SRS §9.1 worked example: floor(399/100) = 3"""
        pytest.skip("not yet implemented")

    def test_zero(self):
        pytest.skip("not yet implemented")
