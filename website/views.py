from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import (
    EditarUsuarioForm,
    RegistroForm,
    RegistroClienteForm,
    RegistroPrestadorForm,
)
from .models import Prestador, Reserva

from django.contrib import messages

from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy

SERVICE_CATALOG = [
    {
        'category': 'Faciales', 'name': 'Facial hidratación profunda',
        'provider': 'RG Beauty Spa', 'duration': '60 min', 'price': '$32.000',
        'time': 'Hoy, 12:30', 'distance': '0,5 km', 'rating': '4.8 (24)',
        'badge': 'Más elegido',
        'image': 'https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=700&q=80',
    },
    {
        'category': 'Peluquería', 'name': 'Corte y brushing',
        'provider': 'Marena Studio', 'duration': '90 min', 'price': '$28.000',
        'time': 'Hoy, 13:15', 'distance': '0,9 km', 'rating': '4.8 (16)',
        'badge': 'Disponible ahora',
        'image': 'https://images.unsplash.com/photo-1562322140-8baeececf3df?w=700&q=80',
    },
    {
        'category': 'Uñas', 'name': 'Manicure permanente',
        'provider': 'Casa Lila', 'duration': '60 min', 'price': '$18.000',
        'time': 'Hoy, 14:00', 'distance': '1,2 km', 'rating': '4.8 (12)',
        'badge': '20% dto.',
        'image': 'https://images.unsplash.com/photo-1610992015732-2449b76344bc?w=700&q=80',
    },
    {
        'category': 'Cejas', 'name': 'Lifting de pestañas',
        'provider': 'Blink Atelier', 'duration': '60 min', 'price': '$26.000',
        'time': 'Hoy, 15:30', 'distance': '1 km', 'rating': '4.9 (18)',
        'badge': 'Mejor evaluado',
        'image': 'https://images.unsplash.com/photo-1583001931096-959e9a1a6223?w=700&q=80',
    },
]

CATEGORIES = [
    ('todo', '✦ Todo'), ('peluqueria', '◒ Peluquería'), ('unas', '◌ Uñas'),
    ('faciales', '◉ Faciales'), ('cejas', '◍ Cejas'), ('pestanas', '◉ Pestañas'),
]


def _filtered_services(request):
    query = request.GET.get('q', '').strip().lower()
    category = request.GET.get('categoria', '').strip().lower()
    services = SERVICE_CATALOG
    if category and category != 'todo':
        category_names = {
            'peluqueria': 'peluquería', 'unas': 'uñas', 'faciales': 'faciales',
            'cejas': 'cejas', 'pestanas': 'pestañas',
        }
        services = [item for item in services if item['category'].lower() == category_names.get(category, category)]
    if query:
        services = [
            item for item in services
            if query in ' '.join((item['category'], item['name'], item['provider'])).lower()
        ]
    return services


# Vista principal
def home(request):
    return render(request, 'website/home.html', {
        'services': _filtered_services(request),
        'categories': CATEGORIES,
    })


def explorar(request):
    return render(request, 'website/explorar.html', {
        'services': _filtered_services(request),
        'categories': CATEGORIES,
    })


@login_required
def reservas(request):
    cliente = getattr(request.user, 'perfil_cliente', None)
    user_reservas = Reserva.objects.filter(
        cliente_idcliente=cliente
    ).prefetch_related('servicios') if cliente else Reserva.objects.none()
    return render(request, 'website/reservas.html', {'reservas': user_reservas})


@login_required
def favoritos(request):
    return render(request, 'website/favoritos.html', {
        'services': _filtered_services(request),
    })

# --------- REGISTRO -------
#Vista de Formulario de Registro (Usuario_Cliente)
def vista_registro(request):
    user_form = RegistroForm(request.POST or None)
    cliente_form = RegistroClienteForm(request.POST or None)

    if request.method == 'POST':
        if user_form.is_valid() and cliente_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                cliente = cliente_form.save(commit=False)
                cliente.usuario = user
                cliente.correo = user.email
                cliente.save()
            login(request, user)
            return redirect('home')

    return render(
        request,
        'website/usuario_formulario.html',
        {
            'user_form': user_form,
            'cliente_form': cliente_form,
            'es_registro': True
        },
    )

@login_required
def vista_editar_informacion_usuario(request):
    user = request.user
    cliente = getattr(user, 'perfil_cliente', None)

    if cliente is None:
        messages.error(request, 'No existe un perfil de cliente asociado.')
        return redirect('home')

    user_form = EditarUsuarioForm(
        request.POST or None,
        instance=user,
    )
    cliente_form = RegistroClienteForm(
        request.POST or None,
        instance=cliente,
    )

    if request.method == 'POST':
        if user_form.is_valid() and cliente_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                cliente = cliente_form.save(commit=False)
                cliente.usuario = user
                cliente.correo = user.email
                cliente.save()
            messages.success(request, f'Datos actualizados correctamente')
            return redirect('home')

    return render(
        request,
        'website/usuario_formulario.html',
        {
            'user_form': user_form,
            'cliente_form': cliente_form,
            'es_registro': False
        },
    )

class CambiarPasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = 'cambiar_contraseña.html'
    success_url = reverse_lazy('cambiar_contraseña/hecho')
    success_message = 'Tu contraseña fue actualizada.'


# --------- SECCIÓN DE PRESTADORES -------
#Vista de Solicitud para Prestadores
@login_required
def vista_solicitud_prestadores(request):
    if hasattr(request.user, 'perfil_prestador'):
        prestador = request.user.perfil_prestador

        if prestador.estado_aprobacion is None:
            messages.info(
                request,
                'Ya tienes una solicitud enviada y en estado de evaluación.',
            )
            return redirect('home')
    
    prestador_form = RegistroPrestadorForm(request.POST or None)

    if request.method == 'POST':
        if prestador_form.is_valid():
            current_user = request.user

            prestador = prestador_form.save(commit=False)
            prestador.usuario = current_user
            prestador.save()
            return redirect('home')

    return render(
        request,
        'website/solicitud_prestador.html',
        {
            'prestador_form': prestador_form
        },
    )

# --------- SECCIÓN DE ADMINISTRADORES -------
@login_required
def vista_administrador(request):
    return render(request, 'website/vista_admin.html', {
        'solicitudes_espera': Prestador.objects.filter(
            estado_aprobacion__isnull=True
        ).select_related('usuario'),
        'solicitudes_aprobadas': Prestador.objects.filter(
            estado_aprobacion=True
        ).select_related('usuario'),
        'solicitudes_rechazadas': Prestador.objects.filter(
            estado_aprobacion=False
        ).select_related('usuario'),
    })

@login_required
def vista_aprobar_rechazar_solicitud(request, pk):
    if request.method != 'POST':
        return redirect('vista_administrador')

    estado = request.POST.get('estado')
    if estado not in {'True', 'False'}:
        messages.error(request, 'El estado de la solicitud no es válido.')
        return redirect('vista_administrador')

    solicitud = get_object_or_404(Prestador, pk=pk)
    solicitud.estado_aprobacion = estado == 'True'
    solicitud.save(update_fields=['estado_aprobacion'])

    messages.success(request, 'El estado de la solicitud fue actualizado.')
    return redirect('vista_administrador')
