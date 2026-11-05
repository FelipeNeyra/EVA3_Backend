from django import forms
from .models import Cliente, Prestador, Servicio
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


class ServicioForm(forms.ModelForm):
    DURACIONES = (
        (30, '30 min'),
        (45, '45 min'),
        (60, '60 min'),
        (90, '90 min'),
        (120, '120 min'),
    )
    categoria = forms.ChoiceField(
        choices=[('', 'Selecciona una categoría'), *Servicio.CATEGORIAS],
        label='Categoría',
        widget=forms.Select(attrs={'class': 'provider-form-control'}),
        error_messages={
            'required': 'Selecciona una categoría.',
            'invalid_choice': 'Selecciona una categoría válida.',
        },
    )
    nombre = forms.CharField(
        max_length=45,
        label='Nombre del servicio',
        widget=forms.TextInput(attrs={
            'class': 'provider-form-control',
            'placeholder': 'Ej. Manicure permanente',
        }),
        error_messages={'required': 'Ingresa el nombre del servicio.'},
    )
    descripcion = forms.CharField(
        max_length=500,
        label='Descripción del servicio',
        widget=forms.Textarea(attrs={
            'class': 'provider-form-control',
            'rows': 3,
            'placeholder': 'Describe qué incluye el servicio.',
        }),
        error_messages={'required': 'Ingresa una descripción del servicio.'},
    )
    duracion = forms.TypedChoiceField(
        choices=DURACIONES,
        coerce=int,
        label='Duración',
        widget=forms.Select(attrs={'class': 'provider-form-control'}),
        error_messages={
            'required': 'Selecciona una duración.',
            'invalid_choice': 'Selecciona una duración válida.',
        },
    )
    precio_base = forms.IntegerField(
        min_value=1000,
        max_value=2147483647,
        label='Precio (CLP)',
        widget=forms.NumberInput(attrs={
            'class': 'provider-form-control',
            'min': 1000,
            'step': 1000,
            'placeholder': '25.000',
        }),
        error_messages={
            'required': 'Ingresa el precio del servicio.',
            'min_value': 'El precio mínimo es $1.000 CLP.',
            'max_value': 'El precio supera el máximo permitido.',
            'invalid': 'Ingresa un precio válido en pesos chilenos.',
        },
    )

    class Meta:
        model = Servicio
        fields = ['categoria', 'nombre', 'descripcion', 'duracion', 'precio_base']

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()
        if not nombre:
            raise forms.ValidationError('Ingresa el nombre del servicio.')
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()
        if not descripcion:
            raise forms.ValidationError('Ingresa una descripción del servicio.')
        return descripcion
