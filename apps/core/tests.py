from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class AuthenticationFlowTests(TestCase):
    def test_student_signup_creates_student_profile_and_logs_user_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "first_name": "Student",
                "last_name": "Demo",
                "email": "student@example.com",
                "username": "student_signup_case",
                "password1": "CampusPass123",
                "password2": "CampusPass123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="student_signup_case").exists())
        user = User.objects.get(username="student_signup_case")
        self.assertEqual(user.profile.role, "student")
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_student_login_redirects_to_home(self):
        user = User.objects.create_user(username="student_login_case", password="CampusPass123")
        user.profile.role = "student"
        user.profile.save(update_fields=["role"])

        response = self.client.post(
            reverse("login"),
            {"username": "student_login_case", "password": "CampusPass123"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("student-dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_guest_booking_redirects_to_login(self):
        response = self.client.get(reverse("seat-booking"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)
