from django import forms
from .models import Cliente, Prestador
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()


class CorreoAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label='Correo electrónico')

    def clean_username(self):
        email = self.cleaned_data['username']
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return email
        except User.MultipleObjectsReturned:
            raise forms.ValidationError(
                'No es posible iniciar sesión con este correo.'
            )
        return user.get_username()


# Formulario de Registro de Usuario (Base de Cuentas)
class RegistroForm(UserCreationForm):
    username = forms.CharField(label='Usuario')
    email = forms.EmailField(label='Correo electrónico')

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(
            email__iexact=email
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este correo ya está registrado')
        return email

class EditarUsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(
            email__iexact=email
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este correo ya está registrado')
        return email


# Formulario de Registro de Cliente
class RegistroClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'direccion_domicilio', 'telefono']

# Formulario de Registro de Prestador
class RegistroPrestadorForm(forms.ModelForm):
    class Meta:
        model = Prestador
        fields = ['especialidad', 'numCertificacion_sanitaria', 'radio_cobertura']
