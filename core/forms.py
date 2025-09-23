from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from core.models import Reserva, Cancha
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
User = get_user_model()

class ReservaForm(forms.Form):
    cancha_id = forms.IntegerField(widget=forms.HiddenInput())
    nombre_contacto = forms.CharField(max_length=120, required=False)
    email_contacto = forms.EmailField(required=False)
    telefono_contacto = forms.CharField(max_length=30, required=False)

    fecha = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    hora_inicio = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    duracion_min = forms.IntegerField(min_value=15, initial=60, help_text="Duración en minutos")

    def clean(self):
        cleaned = super().clean()
        cancha_id = cleaned.get("cancha_id")
        fecha = cleaned.get("fecha")
        hora_inicio = cleaned.get("hora_inicio")
        duracion = cleaned.get("duracion_min")

        if not (cancha_id and fecha and hora_inicio and duracion):
            return cleaned

        try:
            cancha = Cancha.objects.select_related("recinto").get(pk=cancha_id, activa=True)
        except Cancha.DoesNotExist:
            raise ValidationError("Cancha no válida o inactiva.")

        inicio = timezone.make_aware(timezone.datetime.combine(fecha, hora_inicio))
        fin = inicio + timezone.timedelta(minutes=int(duracion))

        # Para no duplicar reglas, construimos una Reserva temporal y dejamos que el modelo valide
        reserva_temp = Reserva(
            cancha=cancha,
            fecha_hora_inicio=inicio,
            fecha_hora_fin=fin,
            estado=Reserva.Estado.PENDIENTE,
            nombre_contacto=cleaned.get("nombre_contacto", ""),
            email_contacto=cleaned.get("email_contacto", ""),
            telefono_contacto=cleaned.get("telefono_contacto", "")
        )
        reserva_temp.full_clean()  # puede lanzar ValidationError con mensajes de dominio

        cleaned["cancha"] = cancha
        cleaned["inicio"] = inicio
        cleaned["fin"] = fin
        return cleaned
    
    User = get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Usaremos este correo para confirmaciones.")
    first_name = forms.CharField(required=False, label="Nombre")
    last_name = forms.CharField(required=False, label="Apellido")

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")
