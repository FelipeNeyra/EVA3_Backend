from .models import Servicio


QUICK_BOOKING_CATEGORIES = (
    ('peluqueria', '♧ Peluquería'),
    ('unas', '◌ Uñas'),
    ('faciales', '☺ Faciales'),
    ('cejas', '⌁ Cejas'),
    ('pestanas', '◉ Pestañas'),
)


def quick_booking(request):
    professionals = {key: [] for key, _ in QUICK_BOOKING_CATEGORIES}
    services = Servicio.objects.filter(
        prestador_idprestador__estado_aprobacion=True,
        prestador_idprestador__usuario__isnull=False,
    ).select_related('prestador_idprestador__usuario')

    for service in services:
        provider = service.prestador_idprestador
        specialty = f'{provider.especialidad} {service.nombre}'.lower()
        categories = {
            'peluqueria': ('peluquer', 'corte', 'brushing'),
            'unas': ('uña', 'manicure', 'pedicure'),
            'faciales': ('facial', 'limpieza', 'masaje facial'),
            'cejas': ('ceja',),
            'pestanas': ('pestaña', 'lifting'),
        }
        name = provider.usuario.get_full_name() or provider.usuario.username
        professional = {
            'service_id': service.idservicio,
            'name': name,
            'specialty': provider.especialidad,
            'service': service.nombre,
            'coverage': provider.radio_cobertura,
            'duration': service.duracion,
            'price': service.precio_base,
        }
        for category, terms in categories.items():
            if any(term in specialty for term in terms):
                if not any(item['name'] == name for item in professionals[category]):
                    professionals[category].append(professional)

    return {
        'quick_booking_categories': QUICK_BOOKING_CATEGORIES,
        'quick_booking_professionals': professionals,
    }
