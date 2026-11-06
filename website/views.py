from datetime import datetime, timedelta
from functools import wraps

from django.shortcuts import redirect, render, get_object_or_404
from django.http import Http404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from .forms import (
    EditarUsuarioForm,
    RegistroForm,
    RegistroClienteForm,
    RegistroPrestadorForm,
    ServicioForm,
)
from .models import (
    Administrador,
    Cliente,
    Liquidacion,
    Pago,
    Prestador,
    Reserva,
    Servicio,
    SuscripcionPrestador,
)

from django.contrib import messages

from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils import timezone
from unicodedata import normalize as unicode_normalize

SERVICE_CATALOG = [
    {
        'category': 'Faciales', 'name': 'Facial hidratación profunda',
        'provider': 'Beauty Go Spa', 'duration': '60 min', 'price': '$32.000',
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

MONTHLY_SUBSCRIPTION_PRICE = 5000


class BeautyGoLoginView(LoginView):
    def get_success_url(self):
        user = self.request.user
        if user.is_superuser or Administrador.objects.filter(usuario_id=user.pk).exists():
            return self.get_redirect_url() or reverse_lazy('vista_administrador')
        return super().get_success_url()


def admin_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or Administrador.objects.filter(usuario_id=request.user.pk).exists()
        ):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped_view


def _format_clp(amount):
    return f'${amount:,.0f}'.replace(',', '.')


def _service_image(category, index=0):
    category_keys = _catalog_category_keys(category)
    if category_keys:
        for item in SERVICE_CATALOG:
            if category_keys[0] in _catalog_category_keys(item['category']):
                return item['image']
    return SERVICE_CATALOG[index % len(SERVICE_CATALOG)]['image']


def _filtered_services(request):
    query = request.GET.get('q', '').strip().lower()
    category = request.GET.get('categoria', '').strip().lower()
    ordering = request.GET.get('orden', 'nombre').strip().lower()
    database_services = Servicio.objects.select_related(
        'prestador_idprestador__usuario'
    ).filter(
        prestador_idprestador__estado_aprobacion=True,
        prestador_idprestador__usuario__isnull=False,
    )
    services = [
        {
            'id': service.idservicio,
            'category': service.categoria or service.prestador_idprestador.especialidad.split(' y ')[0],
            'category_keys': _service_category_keys(service),
            'name': service.nombre,
            'description': service.descripcion,
            'provider': service.prestador_idprestador.usuario.get_full_name()
            or service.prestador_idprestador.usuario.username,
            'duration': f'{service.duracion} min',
            'price': f'${service.precio_base:,.0f}'.replace(',', '.'),
            'time': 'Disponible hoy',
            'distance': service.prestador_idprestador.radio_cobertura,
            'rating': '5.0',
            'badge': 'Disponible ahora',
            'image': _service_image(
                service.categoria or service.prestador_idprestador.especialidad,
                index,
            ),
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
            if query in ' '.join((
                item['category'],
                item['name'],
                item['description'],
                item['provider'],
            )).lower()
        ]
    ordering_key = {
        'precio': lambda item: int(
            item['price'].replace('$', '').replace('.', '')
        ),
        'duracion': lambda item: int(item['duration'].split()[0]),
        'nombre': lambda item: item['name'].lower(),
    }.get(ordering, lambda item: item['name'].lower())
    services.sort(key=ordering_key)
    return services


def _paginated_services(services, request, per_page=6):
    paginator = Paginator(services, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    return page_obj, query_params.urlencode()


def _service_category_keys(service):
    value = unicode_normalize(
        'NFKD',
        f'{service.categoria} {service.prestador_idprestador.especialidad} '
        f'{service.nombre} {service.descripcion}',
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
    services_page, service_querystring = _paginated_services(
        _filtered_services(request),
        request,
    )
    return render(request, 'website/home.html', {
        'services_page': services_page,
        'services': services_page.object_list,
        'service_querystring': service_querystring,
        'categories': CATEGORIES,
        'service_query': request.GET.get('q', '').strip(),
        'service_category': request.GET.get('categoria', 'todo').strip().lower(),
        'service_order': request.GET.get('orden', 'nombre').strip().lower(),
        'booking_dates': [
            timezone.localdate() + timedelta(days=offset)
            for offset in range(1, 8)
        ],
        'booking_client': client_profile,
        'confirmed_booking': confirmed_booking,
        'confirmed_payment': confirmed_payment,
    })


def detalle_servicio(request, pk):
    service = get_object_or_404(
        Servicio.objects.select_related(
            'prestador_idprestador__usuario',
        ),
        pk=pk,
        prestador_idprestador__estado_aprobacion=True,
    )
    provider = service.prestador_idprestador
    return render(request, 'website/detalle_servicio.html', {
        'service': service,
        'provider': provider,
        'service_image': _service_image(service.categoria),
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
        is_administrator = (
            request.user.is_superuser
            or Administrador.objects.filter(usuario_id=request.user.pk).exists()
        )
        if not all((service_id, selected_date, selected_time, contact_name,
                    contact_email, contact_phone, address)):
            messages.error(request, 'Completa todos los datos de la reserva.')
            return redirect('home')
        if cliente is None and not is_administrator:
            messages.error(
                request,
                'Debes tener un perfil de cliente para agendar un servicio.',
            )
            return redirect('home')
        if '@' not in contact_email or len(contact_phone) < 8:
            messages.error(request, 'Revisa tu correo y teléfono antes de continuar.')
            return redirect('home')
        if payment_status != 'success':
            messages.error(request, 'El pago no fue aprobado. La reserva no fue creada.')
            return redirect('home')
        service = get_object_or_404(
            Servicio,
            pk=service_id,
            prestador_idprestador__estado_aprobacion=True,
        )
        try:
            reservation_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            reservation_time = datetime.strptime(selected_time, '%H:%M').time()
        except ValueError:
            messages.error(request, 'La fecha u hora seleccionada no es válida.')
            return redirect('home')
        with transaction.atomic():
            if cliente is None:
                account_email = request.user.email or contact_email
                if Cliente.objects.filter(correo__iexact=account_email).exists():
                    messages.error(
                        request,
                        'El correo de esta cuenta ya está asociado a otro perfil '
                        'de cliente. Contacta al equipo para revisar la cuenta.',
                    )
                    return redirect('home')
                cliente = Cliente.objects.create(
                    nombre=contact_name[:45],
                    correo=account_email,
                    direccion_domicilio=address[:45],
                    telefono=contact_phone[:12],
                    usuario=request.user,
                )
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
    if not hasattr(request.user, 'perfil_cliente'):
        messages.error(
            request,
            'Para postular como prestador primero debes completar tu registro '
            'como cliente.',
        )
        return redirect('datos_usuario')

    if hasattr(request.user, 'perfil_prestador'):
        prestador = request.user.perfil_prestador

        if prestador.estado_aprobacion is None:
            messages.info(
                request,
                'Ya tienes una solicitud enviada y en estado de evaluación.',
            )
            return redirect('home')
        if prestador.estado_aprobacion:
            return redirect('vista_prestador')
        messages.info(
            request,
            'Tu solicitud fue rechazada. Contacta al equipo para obtener ayuda.',
        )
        return redirect('home')
    
    prestador_form = RegistroPrestadorForm(request.POST or None)

    if request.method == 'POST':
        if prestador_form.is_valid():
            current_user = request.user

            prestador = prestador_form.save(commit=False)
            prestador.usuario = current_user
            prestador.save()
            messages.success(
                request,
                'Tu solicitud fue enviada y está pendiente de revisión.',
            )
            return redirect('home')

    return render(
        request,
        'website/solicitud_prestador.html',
        {
            'prestador_form': prestador_form
        },
    )


@login_required
def vista_prestador(request):
    prestador = getattr(request.user, 'perfil_prestador', None)
    if prestador is None:
        raise PermissionDenied

    section = request.GET.get('section', 'servicios')
    if section not in {'servicios', 'reservas', 'suscripcion'}:
        section = 'servicios'

    service_form = ServicioForm()
    editing_service = None
    deleting_service = None
    requested_service_id = request.GET.get('editar')
    requested_delete_service_id = request.GET.get('eliminar')
    if requested_service_id and section == 'servicios':
        if not requested_service_id.isdigit():
            raise Http404
        editing_service = get_object_or_404(
            Servicio,
            pk=int(requested_service_id),
            prestador_idprestador=prestador,
        )
        service_form = ServicioForm(instance=editing_service)

    if requested_delete_service_id and section == 'servicios':
        if not requested_delete_service_id.isdigit():
            raise Http404
        deleting_service = get_object_or_404(
            Servicio,
            pk=int(requested_delete_service_id),
            prestador_idprestador=prestador,
        )

    if request.method == 'POST':
        if prestador.estado_aprobacion is not True:
            messages.error(
                request,
                'Solo los perfiles aprobados pueden administrar servicios, '
                'reservas y suscripciones.',
            )
            return redirect('vista_prestador')

        action = request.POST.get('action')
        if action == 'pagar_suscripcion':
            current_period = timezone.localdate().replace(day=1)
            subscription, _ = SuscripcionPrestador.objects.get_or_create(
                prestador=prestador,
                periodo=current_period,
                defaults={'monto': MONTHLY_SUBSCRIPTION_PRICE},
            )
            if subscription.estado == SuscripcionPrestador.PAGADA:
                messages.info(request, 'La suscripción de este mes ya está pagada.')
            else:
                subscription.estado = SuscripcionPrestador.PAGADA
                subscription.monto = MONTHLY_SUBSCRIPTION_PRICE
                subscription.fecha_pago = timezone.now()
                subscription.registrado_por = request.user
                subscription.save(update_fields=[
                    'estado',
                    'monto',
                    'fecha_pago',
                    'registrado_por',
                ])
                messages.success(
                    request,
                    'Pago simulado correctamente. Tu suscripción está al día.',
                )
            return redirect(f"{reverse_lazy('vista_prestador')}?section=suscripcion")
        elif action == 'guardar_servicio':
            service_id = request.POST.get('service_id')
            if service_id and not service_id.isdigit():
                messages.error(request, 'El servicio seleccionado no es válido.')
                return redirect('vista_prestador')
            editing_service = (
                get_object_or_404(
                    Servicio,
                    pk=int(service_id),
                    prestador_idprestador=prestador,
                )
                if service_id else None
            )
            service_form = ServicioForm(
                request.POST,
                instance=editing_service,
            )
            if service_form.is_valid():
                with transaction.atomic():
                    service = service_form.save(commit=False)
                    if editing_service is None:
                        service.idservicio = (
                            Servicio.objects.order_by('-idservicio')
                            .values_list('idservicio', flat=True)
                            .first() or 0
                        ) + 1
                    service.prestador_idprestador = prestador
                    service.save()
                messages.success(request, 'El servicio fue guardado correctamente.')
                return redirect('vista_prestador')
            section = 'servicios'
        elif action == 'eliminar_servicio':
            service_id = request.POST.get('service_id', '')
            if not service_id.isdigit():
                messages.error(request, 'El servicio seleccionado no es válido.')
                return redirect('vista_prestador')
            service = get_object_or_404(
                Servicio,
                pk=int(service_id),
                prestador_idprestador=prestador,
            )
            service.delete()
            messages.success(request, 'El servicio fue eliminado correctamente.')
            return redirect('vista_prestador')
        elif action == 'actualizar_reserva':
            status = request.POST.get('estado')
            reservation_id = request.POST.get('reserva_id', '')
            if not reservation_id.isdigit():
                messages.error(request, 'La reserva seleccionada no es válida.')
                return redirect(f"{reverse_lazy('vista_prestador')}?section=reservas")
            if status not in {'Confirmada', 'Rechazada', 'Completada'}:
                messages.error(request, 'El estado de la reserva no es válido.')
            else:
                reservation = get_object_or_404(
                    Reserva,
                    pk=int(reservation_id),
                    servicios__prestador_idprestador=prestador,
                )
                reservation.estado = status
                reservation.save(update_fields=['estado'])
                messages.success(request, 'El estado de la reserva fue actualizado.')
            return redirect(f"{reverse_lazy('vista_prestador')}?section=reservas")
        else:
            messages.error(request, 'La acción solicitada no es válida.')
            return redirect('vista_prestador')

    provider_services = list(
        Servicio.objects.filter(prestador_idprestador=prestador)
        .order_by('nombre')
    )
    provider_query = request.GET.get('q', '').strip().lower()
    provider_category = request.GET.get('categoria', '').strip().lower()
    provider_order = request.GET.get('orden', 'nombre').strip().lower()
    if provider_query:
        provider_services = [
            service for service in provider_services
            if provider_query in ' '.join((
                service.nombre,
                service.descripcion,
                service.categoria,
                prestador.especialidad,
            )).lower()
        ]
    if provider_category and provider_category != 'todo':
        provider_services = [
            service for service in provider_services
            if provider_category in _service_category_keys(service)
        ]
    if provider_order == 'precio':
        provider_services.sort(key=lambda service: service.precio_base)
    elif provider_order == 'duracion':
        provider_services.sort(key=lambda service: service.duracion)
    else:
        provider_services.sort(key=lambda service: service.nombre.lower())
    provider_services_page, provider_querystring = _paginated_services(
        provider_services,
        request,
    )
    services = [
        {
            'service': service,
            'image': _service_image(service.categoria, index),
            'price_display': _format_clp(service.precio_base),
        }
        for index, service in enumerate(provider_services_page.object_list)
    ]
    reservation_list = list(
        Reserva.objects.filter(
            servicios__prestador_idprestador=prestador,
        ).distinct().select_related('cliente_idcliente').prefetch_related('servicios')
        .order_by('-fecha', '-hora_bloque')
    )
    for reservation in reservation_list:
        reservation.provider_services = [
            service for service in reservation.servicios.all()
            if service.prestador_idprestador_id == prestador.pk
        ]
    current_period = timezone.localdate().replace(day=1)
    subscription = SuscripcionPrestador.objects.filter(
        prestador=prestador,
        periodo=current_period,
    ).first()
    subscription_history = []
    for history_item in SuscripcionPrestador.objects.filter(
        prestador=prestador,
    ).exclude(periodo=current_period):
        subscription_history.append({
            'subscription': history_item,
            'amount_display': _format_clp(history_item.monto),
            'is_overdue': (
                history_item.periodo < current_period
                and history_item.estado == SuscripcionPrestador.PENDIENTE
            ),
        })

    return render(request, 'website/vista_prestador.html', {
        'prestador': prestador,
        'section': section,
        'service_form': service_form,
        'editing_service': editing_service,
        'deleting_service': deleting_service,
        'services': services,
        'service_page': provider_services_page,
        'service_querystring': provider_querystring,
        'service_query': request.GET.get('q', '').strip(),
        'service_category': provider_category or 'todo',
        'service_order': provider_order,
        'categories': CATEGORIES,
        'service_count': len(provider_services),
        'reservations': reservation_list,
        'reservation_count': len(reservation_list),
        'current_period': current_period,
        'subscription': subscription,
        'subscription_history': subscription_history,
        'monthly_subscription_price': _format_clp(MONTHLY_SUBSCRIPTION_PRICE),
    })


# --------- SECCIÓN DE ADMINISTRADORES -------
@admin_required
def vista_administrador(request):
    providers = Prestador.objects.select_related('usuario').filter(
        usuario__isnull=False,
    )
    pending_requests = providers.filter(
        estado_aprobacion__isnull=True,
    ).order_by('usuario__date_joined', 'pk')
    approved_providers = providers.filter(
        estado_aprobacion=True,
    ).order_by('usuario__first_name', 'usuario__last_name', 'pk')
    rejected_requests = providers.filter(
        estado_aprobacion=False,
    ).order_by('usuario__first_name', 'usuario__last_name', 'pk')

    section = request.GET.get('section', 'solicitudes')
    if section not in {'solicitudes', 'suscripciones', 'liquidaciones'}:
        section = 'solicitudes'

    provider_list = list(providers.order_by('usuario__date_joined', 'pk'))
    selected_provider = None
    requested_provider_id = request.GET.get('prestador')
    if requested_provider_id:
        selected_provider = next(
            (provider for provider in provider_list
             if str(provider.pk) == requested_provider_id),
            None,
        )
    if selected_provider is None:
        selected_provider = pending_requests.first() or (
            provider_list[0] if provider_list else None
        )

    current_period = timezone.localdate().replace(day=1)
    subscriptions = {
        subscription.prestador_id: subscription
        for subscription in SuscripcionPrestador.objects.filter(
            periodo=current_period,
            prestador__estado_aprobacion=True,
        )
    }
    subscription_rows = []
    for provider in approved_providers:
        subscription = subscriptions.get(provider.pk)
        subscription_rows.append({
            'prestador': provider,
            'subscription': subscription,
            'amount_display': _format_clp(
                subscription.monto if subscription else MONTHLY_SUBSCRIPTION_PRICE
            ),
        })
    pending_subscriptions = sum(
        row['subscription'] is None
        or row['subscription'].estado == SuscripcionPrestador.PENDIENTE
        for row in subscription_rows
    )
    liquidation_count = Liquidacion.objects.count()
    liquidations = list(
        Liquidacion.objects.select_related(
            'administrador_idadministrador__usuario',
        ).prefetch_related(
            'servicios__prestador_idprestador__usuario',
        ).order_by('-idliquidacion')
    ) if section == 'liquidaciones' else []
    liquidation_rows = [
        {
            'liquidation': liquidation,
            'gross_display': _format_clp(liquidation.monto_bruto_total),
            'commission_display': _format_clp(liquidation.monto_comision_spa),
            'net_display': _format_clp(liquidation.monto_neto_prestador),
        }
        for liquidation in liquidations
    ]

    return render(request, 'website/vista_admin.html', {
        'section': section,
        'pending_requests': pending_requests,
        'approved_providers': approved_providers,
        'rejected_requests': rejected_requests,
        'selected_provider': selected_provider,
        'pending_request_count': pending_requests.count(),
        'approved_provider_count': approved_providers.count(),
        'rejected_request_count': rejected_requests.count(),
        'subscription_rows': subscription_rows,
        'pending_subscription_count': pending_subscriptions,
        'current_period': current_period,
        'monthly_subscription_price': _format_clp(MONTHLY_SUBSCRIPTION_PRICE),
        'liquidation_count': liquidation_count,
        'liquidation_rows': liquidation_rows,
    })


@admin_required
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
    return redirect(f"{reverse_lazy('vista_administrador')}?section=solicitudes&prestador={pk}")


@admin_required
def vista_actualizar_suscripcion(request, pk):
    if request.method != 'POST':
        return redirect('vista_administrador')

    estado = request.POST.get('estado')
    if estado not in {SuscripcionPrestador.PENDIENTE, SuscripcionPrestador.PAGADA}:
        messages.error(request, 'El estado de suscripción no es válido.')
        return redirect(
            f"{reverse_lazy('vista_administrador')}?section=suscripciones"
        )

    prestador = get_object_or_404(
        Prestador,
        pk=pk,
        estado_aprobacion=True,
    )
    periodo = timezone.localdate().replace(day=1)
    subscription, _ = SuscripcionPrestador.objects.get_or_create(
        prestador=prestador,
        periodo=periodo,
        defaults={'monto': MONTHLY_SUBSCRIPTION_PRICE},
    )
    subscription.estado = estado
    subscription.monto = MONTHLY_SUBSCRIPTION_PRICE
    subscription.fecha_pago = (
        timezone.now() if estado == SuscripcionPrestador.PAGADA else None
    )
    subscription.registrado_por = request.user
    subscription.save(update_fields=[
        'estado',
        'monto',
        'fecha_pago',
        'registrado_por',
    ])

    messages.success(request, 'El estado de la suscripción fue actualizado.')
    return redirect(
        f"{reverse_lazy('vista_administrador')}?section=suscripciones"
    )
