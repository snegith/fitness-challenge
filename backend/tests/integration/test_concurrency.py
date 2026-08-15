"""
Integration tests — concurrency.

Coverage (SRS §11.6):
    - Two simultaneous POST /api/auth/register requests with identical names:
        exactly one returns 201, the other returns 409 USER_ALREADY_EXISTS.
        No additional rows must be created.

The uniqueness guarantee comes from the UNIQUE INDEX idx_users_name_key at the
database level — not just an app-level check-then-insert pattern (SRS NFR-2).
"""

import pytest


class TestConcurrentRegistration:
    def test_simultaneous_identical_registration(self, client):
        """
        Fire two concurrent register requests with the same name.
        Exactly one must succeed (201); the other must return 409.
        """
        pytest.skip("not yet implemented")
