from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Permiso, Rol, RolPermiso, Usuario

class LoginForm(forms.Form):

    nombre_usuario = forms.CharField(
        label="Usuario",
        max_length=60,
        required=True,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "gerencia",
            "autocomplete": "username"
        }),
        error_messages={
            "required": "Ingrese su nombre de usuario."
        }
    )

    password = forms.CharField(
        label="Contraseña",
        max_length=128,
        required=True,
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "••••••••••",
            "autocomplete": "current-password"
        }),
        error_messages={
            "required": "Ingrese su contraseña."
        }
    )

class UsuarioCreacionForm(forms.ModelForm):

    password = forms.CharField(
        label="Contraseña",
        min_length=12,
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Ingrese una contraseña segura",
            "autocomplete": "new-password"
        })
    )

    confirmar_password = forms.CharField(
        label="Confirmar contraseña",
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Repita la contraseña",
            "autocomplete": "new-password"
        })
    )

    roles = forms.ModelMultipleChoiceField(
        label="Roles asignados",
        queryset=Rol.objects.filter(
            activo=True
        ).order_by("nombre"),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:

        model = Usuario

        fields = [
            "nombres",
            "apellidos",
            "documento",
            "correo",
            "nombre_usuario",
        ]

        labels = {
            "nombres": "Nombres",
            "apellidos": "Apellidos",
            "documento": "Documento de identidad",
            "correo": "Correo electrónico",
            "nombre_usuario": "Nombre de usuario",
        }

    def clean(self):

        datos = super().clean()

        password = datos.get("password")
        confirmar = datos.get("confirmar_password")

        if password and confirmar:

            if password != confirmar:

                self.add_error(
                    "confirmar_password",
                    "Las contraseñas no coinciden."
                )

        if password:

            usuario = Usuario(
                nombres=datos.get("nombres", ""),
                apellidos=datos.get("apellidos", ""),
                correo=datos.get("correo", ""),
                nombre_usuario=datos.get("nombre_usuario", "")
            )

            try:

                validate_password(password, user=usuario)

            except ValidationError as error:

                self.add_error("password", error)

        return datos
    # ==========================================
# FORMULARIO DE EDICIÓN DE USUARIOS
# ==========================================

class UsuarioEdicionForm(forms.ModelForm):

    class Meta:

        model = Usuario

        fields = [
            "nombres",
            "apellidos",
            "documento",
            "correo",
            "nombre_usuario",
        ]

        labels = {
            "nombres": "Nombres",
            "apellidos": "Apellidos",
            "documento": "Documento de identidad",
            "correo": "Correo electrónico",
            "nombre_usuario": "Nombre de usuario",
        }

    def clean_correo(self):

        return self.cleaned_data["correo"].strip().lower()

    def clean_nombre_usuario(self):

        return self.cleaned_data["nombre_usuario"].strip()


class UsuarioRolesForm(forms.Form):
    roles = forms.ModelMultipleChoiceField(
        label="Roles asignados",
        queryset=Rol.objects.filter(activo=True).order_by("nombre"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )


class UsuarioRestablecerPasswordForm(forms.Form):
    password = forms.CharField(
        label="Nueva contraseña",
        min_length=12,
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    confirmar_password = forms.CharField(
        label="Confirmar contraseña",
        max_length=128,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean(self):
        datos = super().clean()
        password = datos.get("password")
        confirmar = datos.get("confirmar_password")
        if password and confirmar and password != confirmar:
            self.add_error("confirmar_password", "Las contraseñas no coinciden.")
        if password:
            try:
                validate_password(password, user=self.usuario)
            except ValidationError as error:
                self.add_error("password", error)
        return datos


class RolForm(forms.ModelForm):
    class Meta:
        model = Rol
        fields = ("nombre", "descripcion")
        labels = {"nombre": "Nombre del rol", "descripcion": "Descripción"}
        widgets = {
            "nombre": forms.TextInput(attrs={"autocomplete": "off", "maxlength": 80}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_nombre(self):
        nombre = " ".join(self.cleaned_data["nombre"].split()).upper()
        existentes = Rol.objects.filter(nombre__iexact=nombre)
        if self.instance and self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise ValidationError("Ya existe un rol con ese nombre.")
        return nombre


class RolPermisosForm(forms.Form):
    permisos = forms.ModelMultipleChoiceField(
        label="Permisos del rol",
        queryset=Permiso.objects.order_by("modulo", "codigo"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
