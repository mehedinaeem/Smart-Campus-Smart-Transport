from django import forms

from apps.core.models import UserProfile


class RoleAssignmentForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput())
    role = forms.ChoiceField(
        choices=[
            (UserProfile.ROLE_STUDENT, "Student"),
            (UserProfile.ROLE_DRIVER, "Driver"),
        ],
    )
