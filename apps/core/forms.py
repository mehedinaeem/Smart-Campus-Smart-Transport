from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "auth-input", "placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "auth-input", "placeholder": "Password"}))


class StudentSignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "auth-input", "placeholder": "First name"}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={"class": "auth-input", "placeholder": "Last name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "auth-input", "placeholder": "Email address"}))
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "auth-input", "placeholder": "Username"}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "auth-input", "placeholder": "Create password"}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "auth-input", "placeholder": "Confirm password"}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "email", "username", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            user.profile.role = "student"
            user.profile.save(update_fields=["role"])
        return user
