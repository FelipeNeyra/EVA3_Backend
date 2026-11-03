from datetime import datetime, timedelta

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
from .models import Pago, Prestador, Reserva, Servicio

from django.contrib import messages

from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils import timezone
from unicodedata import normalize as unicode_normalize

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
    database_services = Servicio.objects.select_related(
        'prestador_idprestador__usuario'
    ).order_by('idservicio')
    services = [
        {
            'id': service.idservicio,
            'category': service.prestador_idprestador.especialidad.split(' y ')[0],
            'category_keys': _service_category_keys(service),
            'name': service.nombre,
            'provider': service.prestador_idprestador.usuario.get_full_name()
            or service.prestador_idprestador.usuario.username,
            'duration': f'{service.duracion} min',
            'price': f'${service.precio_base:,.0f}'.replace(',', '.'),
            'time': 'Disponible hoy',
            'distance': service.prestador_idprestador.radio_cobertura,
            'rating': '5.0',
            'badge': 'Disponible ahora',
            'image': SERVICE_CATALOG[index % len(SERVICE_CATALOG)]['image'],
        }
        for index, service in enumerate(database_services)
    ]
    if not services:
        services = [
            {
                **item,
                'id': None,
                'category_keys': _catalog_category_keys(item['category']),
            }
            for item in SERVICE_CATALOG
        ]
    if category and category != 'todo':
        services = [item for item in services if category in item['category_keys']]
    if query:
        services = [
            item for item in services
            if query in ' '.join((item['category'], item['name'], item['provider'])).lower()
        ]
    return services


def _service_category_keys(service):
    value = unicode_normalize(
        'NFKD',
        f'{service.prestador_idprestador.especialidad} {service.nombre}',
    ).encode('ascii', 'ignore').decode().lower()
    terms = {
        'peluqueria': ('peluquer', 'corte', 'brushing'),
        'unas': ('una', 'manicure', 'pedicure'),
        'faciales': ('facial', 'limpieza', 'masaje facial'),
        'cejas': ('ceja',),
        'pestanas': ('pestana', 'lifting'),
    }
    return [
        category for category, keywords in terms.items()
        if any(keyword in value for keyword in keywords)
    ]


def _catalog_category_keys(category):
    value = unicode_normalize('NFKD', category).encode('ascii', 'ignore').decode().lower()
    return {
        'peluqueria': ['peluqueria'],
        'unas': ['unas'],
        'faciales': ['faciales'],
        'cejas': ['cejas'],
        'pestanas': ['pestanas'],
    }.get(value, [])


# Vista principal
def home(request):
    client_profile = getattr(request.user, 'perfil_cliente', None)
    confirmed_booking = None
    if request.GET.get('reserva') == 'confirmada' and client_profile:
        confirmed_booking = Reserva.objects.filter(
            idreserva=request.GET.get('id'),
            cliente_idcliente=client_profile,
        ).prefetch_related('servicios').first()
    confirmed_payment = (
        Pago.objects.filter(reserva_idreserva=confirmed_booking).first()
        if confirmed_booking else None
    )
    return render(request, 'website/home.html', {
        'services': _filtered_services(request),
        'categories': CATEGORIES,
        'booking_dates': [
            timezone.localdate() + timedelta(days=offset)
            for offset in range(1, 8)
        ],
        'booking_client': client_profile,
        'confirmed_booking': confirmed_booking,
        'confirmed_payment': confirmed_payment,
    })


@login_required
def reservas(request):
    if request.method == 'POST':
        cliente = getattr(request.user, 'perfil_cliente', None)
        service_id = request.POST.get('service_id')
        selected_date = request.POST.get('date')
        selected_time = request.POST.get('time')
        contact_name = request.POST.get('contact_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        address = request.POST.get('address', '').strip()
        payment_status = request.POST.get('payment_status')
        if not all((cliente, service_id, selected_date, selected_time, contact_name,
                    contact_email, contact_phone, address)):
            messages.error(request, 'Completa todos los datos de la reserva.')
            return redirect('home')
        if '@' not in contact_email or len(contact_phone) < 8:
            messages.error(request, 'Revisa tu correo y teléfono antes de continuar.')
            return redirect('home')
        if payment_status != 'success':
            messages.error(request, 'El pago no fue aprobado. La reserva no fue creada.')
            return redirect('home')
        service = get_object_or_404(Servicio, pk=service_id)
        try:
            reservation_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            reservation_time = datetime.strptime(selected_time, '%H:%M').time()
        except ValueError:
            messages.error(request, 'La fecha u hora seleccionada no es válida.')
            return redirect('home')
        reservation = Reserva.objects.create(
            idreserva=(Reserva.objects.order_by('-idreserva').values_list(
                'idreserva', flat=True
            ).first() or 0) + 1,
            fecha=reservation_date,
            hora_bloque=timezone.make_aware(
                datetime.combine(reservation_date, reservation_time)
            ),
            direccion_visita=address[:45],
            estado='Pendiente',
            cliente_idcliente=cliente,
        )
        reservation.servicios.add(service)
        Pago.objects.create(
            idpago=(Pago.objects.order_by('-idpago').values_list(
                'idpago', flat=True
            ).first() or 0) + 1,
            monto_total=round(service.precio_base * 0.3),
            metodo_pago='Simulación Webpay aprobada',
            reserva_idreserva=reservation,
        )
        return redirect(f'/?reserva=confirmada&id={reservation.idreserva}')

    cliente = getattr(request.user, 'perfil_cliente', None)
    user_reservas = Reserva.objects.filter(
        cliente_idcliente=cliente
    ).prefetch_related('servicios').order_by('-fecha', '-hora_bloque') if cliente else Reserva.objects.none()
    reservation_cards = []
    for index, reserva in enumerate(user_reservas):
        service = reserva.servicios.select_related(
            'prestador_idprestador__usuario'
        ).first()
        payment = Pago.objects.filter(reserva_idreserva=reserva).first()
        if service:
            provider = service.prestador_idprestador
            reservation_cards.append({
                'reservation': reserva,
                'service': service,
                'provider': provider.usuario.get_full_name() or provider.usuario.username,
                'specialty': provider.especialidad,
                'payment': payment,
                'image': SERVICE_CATALOG[index % len(SERVICE_CATALOG)]['image'],
            })
    return render(request, 'website/reservas.html', {
        'reservations': reservation_cards,
        'booking_client': cliente,
    })


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
