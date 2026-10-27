from django import forms
from .models import Cliente, Prestador
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()

# Formulario de Registro de Usuario (Base de Cuentas)
class RegistroForm(UserCreationForm):
    username = forms.CharField(label='Usuario')
    email = forms.EmailField(label='Correo electrónico')

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ese correo ya está asociado a un usuario')
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
        fields = ['especialidad', 'id_certificacion_sanitaria', 'radio_cobertura']