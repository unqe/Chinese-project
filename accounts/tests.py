"""
Unit tests for the accounts app.
Covers UserProfile auto-creation, get_full_address(), profile view,
and account deletion.
"""

from django.test import TestCase
from django.contrib.auth.models import User

from accounts.models import UserProfile


# ---------------------------------------------------------------------------
# UserProfile model
# ---------------------------------------------------------------------------

class UserProfileAutoCreateTest(TestCase):
    """UserProfile is created automatically on User creation via signal."""

    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(username="newuser", password="pass123")
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, UserProfile)

    def test_profile_is_one_to_one_with_user(self):
        user = User.objects.create_user(username="onetoone", password="pass123")
        self.assertEqual(user.profile.user, user)

    def test_profile_str_includes_username(self):
        user = User.objects.create_user(username="struser", password="pass123")
        self.assertIn("struser", str(user.profile))

    def test_profile_created_once_not_duplicated(self):
        user = User.objects.create_user(username="once", password="pass123")
        # Saving user again should not create a second profile
        user.first_name = "Updated"
        user.save()
        count = UserProfile.objects.filter(user=user).count()
        self.assertEqual(count, 1)

    def test_profile_default_values_empty(self):
        user = User.objects.create_user(username="defaults", password="pass123")
        profile = user.profile
        self.assertEqual(profile.phone, "")
        self.assertEqual(profile.address_line1, "")
        self.assertEqual(profile.city, "")
        self.assertEqual(profile.postcode, "")
        self.assertFalse(profile.marketing_opt_in)


class UserProfileGetFullAddressTest(TestCase):
    """UserProfile.get_full_address() formats saved address correctly."""

    def setUp(self):
        self.user = User.objects.create_user(username="addruser", password="pass123")
        self.profile = self.user.profile

    def test_full_address_with_all_fields(self):
        self.profile.address_line1 = "123 Dragon Road"
        self.profile.address_line2 = "Flat 2"
        self.profile.city = "London"
        self.profile.postcode = "E1 1AA"
        addr = self.profile.get_full_address()
        self.assertIn("123 Dragon Road", addr)
        self.assertIn("Flat 2", addr)
        self.assertIn("London", addr)
        self.assertIn("E1 1AA", addr)

    def test_full_address_skips_blank_parts(self):
        self.profile.address_line1 = "10 Noodle Lane"
        self.profile.city = "Manchester"
        self.profile.postcode = "M1 2BC"
        addr = self.profile.get_full_address()
        # address_line2 is blank so it should not add an empty comma segment
        self.assertNotIn(",,", addr)
        self.assertIn("10 Noodle Lane", addr)

    def test_full_address_empty_when_nothing_saved(self):
        addr = self.profile.get_full_address()
        self.assertEqual(addr, "")


# ---------------------------------------------------------------------------
# Profile view
# ---------------------------------------------------------------------------

class ProfileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="profileuser", password="pass123")

    def test_profile_page_redirects_if_not_logged_in(self):
        response = self.client.get("/profile/")
        self.assertRedirects(
            response,
            "/accounts/login/?next=/profile/",
            fetch_redirect_response=False,
        )

    def test_profile_page_loads_when_logged_in(self):
        self.client.login(username="profileuser", password="pass123")
        response = self.client.get("/profile/")
        self.assertEqual(response.status_code, 200)

    def test_profile_update_saves_phone(self):
        self.client.login(username="profileuser", password="pass123")
        self.client.post("/profile/", {
            "first_name": "Test",
            "last_name": "User",
            "phone": "07912345678",
            "address_line1": "",
            "address_line2": "",
            "city": "",
            "postcode": "",
            "marketing_opt_in": False,
        })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.phone, "07912345678")


# ---------------------------------------------------------------------------
# Account deletion view
# ---------------------------------------------------------------------------

class DeleteAccountViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="deleteuser", password="deleteme99"
        )

    def test_delete_account_removes_user(self):
        self.client.login(username="deleteuser", password="deleteme99")
        self.client.post("/profile/delete/", {"password": "deleteme99"})
        self.assertFalse(User.objects.filter(username="deleteuser").exists())

    def test_wrong_password_does_not_delete(self):
        self.client.login(username="deleteuser", password="deleteme99")
        self.client.post("/profile/delete/", {"password": "wrongpass"})
        self.assertTrue(User.objects.filter(username="deleteuser").exists())
