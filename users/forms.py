# users/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Correo electrónico")

    class Meta:
        model = User
        # Campos visibles en el formulario
        fields = ("username", "email", "password1", "password2")

        # Etiquetas personalizadas (opcional)
        labels = {
            "username": "Nombre de usuario",
            "email": "Correo electrónico",
            "password1": "Contraseña",
            "password2": "Repite la contraseña",
        }

        help_texts = {
            "username": None,
        }

    def clean_email(self):
        """
        Evita que se registren dos usuarios con el mismo email.
        """
        email = self.cleaned_data.get("email").lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este correo.")
        return email

    def save(self, commit=True):
        """
        Guarda el usuario nuevo y define valores por defecto si aplica.
        """
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()

        # Si tu modelo tiene 'rol', asigna un valor por defecto
        if hasattr(user, "rol") and not user.rol:
            user.rol = "CLIENTE"

        if commit:
            user.save()
        return user

class SignUpForm(UserCreationForm):
    """
    Formulario de registro de nuevos usuarios.
    Usa el modelo de usuario personalizado (AUTH_USER_MODEL).
    """

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]
        labels = {
            "username": "Nombre de usuario",
            "email": "Correo electrónico",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "password1": "Contraseña",
            "password2": "Confirmar contraseña",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mejora la apariencia de los campos
        for field_name, field in self.fields.items():
            field.widget.attrs.update({"class": "form-control"})


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        # Quita "email" de aquí para que no pueda modificarse
        fields = ["first_name", "last_name", "username"]
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "username": "Usuario",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({"class": "form-control"})
        # Si NO quieres permitir cambiar el username, descomenta:
        # self.fields["username"].disabled = True

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.exclude(pk=self.instance.pk).filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe otra cuenta con este correo.")
        return email
