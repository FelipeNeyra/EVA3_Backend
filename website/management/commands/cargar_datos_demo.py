from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from website.models import (
    Administrador,
    Cliente,
    Liquidacion,
    Pago,
    Prestador,
    Reserva,
    Servicio,
    ServicioHasLiquidacion,
)


User = get_user_model()


class Command(BaseCommand):
    help = 'Carga datos ficticios y coherentes para probar RG Beauty.'

    @transaction.atomic
    def handle(self, *args, **options):
        admin_user = self._user(
            username='admin_demo',
            email='admin@rgbeauty.demo',
            first_name='Camila',
            last_name='Administración',
            password='Demo12345!',
        )
        administrador, _ = Administrador.objects.get_or_create(
            usuario=admin_user,
            defaults={'idadministrador': 1},
        )

        clients = [
            ('sofia.cliente@rgbeauty.demo', 'Sofía Martínez', 'Pasaje Los Aromos 245', '+56987654321'),
            ('valentina.cliente@rgbeauty.demo', 'Valentina Rojas', 'Avenida Copayapu 1180', '+56976543210'),
        ]
        client_profiles = []
        for email, name, address, phone in clients:
            user = self._user(
                username=email.split('@')[0],
                email=email,
                first_name=name.split()[0],
                last_name=' '.join(name.split()[1:]),
                password='Demo12345!',
            )
            client, _ = Cliente.objects.update_or_create(
                usuario=user,
                defaults={
                    'nombre': name,
                    'correo': email,
                    'direccion_domicilio': address,
                    'telefono': phone,
                    'nivel_acceso': 'cliente',
                },
            )
            client_profiles.append(client)

        provider_data = [
            ('marena.studio@rgbeauty.demo', 'Marena Studio', 'Peluquería', 'CERT-PEL-001', '5 km'),
            ('casa.lila@rgbeauty.demo', 'Casa Lila', 'Uñas', 'CERT-UNA-002', '4 km'),
            ('blink.atelier@rgbeauty.demo', 'Blink Atelier', 'Cejas y pestañas', 'CERT-CEJ-003', '6 km'),
            ('rg.spa@rgbeauty.demo', 'RG Beauty Spa', 'Faciales', 'CERT-FAC-004', '5 km'),
            ('camila.soto@rgbeauty.demo', 'Camila Soto', 'Peluquería', 'CERT-PEL-005', '3 km'),
            ('antonia.perez@rgbeauty.demo', 'Antonia Pérez', 'Faciales', 'CERT-FAC-006', '4 km'),
            ('sofia.nails@rgbeauty.demo', 'Sofía Nails', 'Uñas', 'CERT-UNA-007', '7 km'),
            ('cejas.vale@rgbeauty.demo', 'Valentina Beauty', 'Cejas y pestañas', 'CERT-CEJ-008', '5 km'),
        ]
        providers = []
        for email, name, specialty, certificate, coverage in provider_data:
            user = self._user(
                username=email.split('@')[0],
                email=email,
                first_name=name.split()[0],
                last_name=' '.join(name.split()[1:]),
                password='Demo12345!',
            )
            provider, _ = Prestador.objects.update_or_create(
                usuario=user,
                defaults={
                    'especialidad': specialty,
                    'numCertificacion_sanitaria': certificate,
                    'radio_cobertura': coverage,
                    'estado_aprobacion': True,
                    'nivel_acceso': 'prestador',
                },
            )
            Cliente.objects.update_or_create(
                usuario=user,
                defaults={
                    'nombre': name,
                    'correo': email,
                    'direccion_domicilio': 'Copiapó',
                    'telefono': '+56912345678',
                    'nivel_acceso': 'cliente',
                },
            )
            providers.append(provider)

        service_data = [
            ('Corte y brushing', 90, 28000, providers[0]),
            ('Manicure permanente', 60, 18000, providers[1]),
            ('Lifting de pestañas', 60, 26000, providers[2]),
            ('Facial hidratación profunda', 60, 32000, providers[3]),
            ('Diseño de cejas', 45, 14000, providers[2]),
            ('Masaje facial relajante', 45, 22000, providers[3]),
            ('Coloración y peinado', 120, 42000, providers[4]),
            ('Kapping de uñas', 75, 24000, providers[6]),
            ('Limpieza facial express', 40, 18000, providers[5]),
            ('Perfilado y laminado', 50, 20000, providers[7]),
            ('Extensiones de pestañas', 90, 30000, providers[7]),
        ]
        services = []
        for name, duration, price, provider in service_data:
            service, _ = Servicio.objects.update_or_create(
                nombre=name,
                prestador_idprestador=provider,
                defaults={
                    'idservicio': self._existing_service_id(name, provider),
                    'duracion': duration,
                    'precio_base': price,
                },
            )
            services.append(service)

        reservation, _ = Reserva.objects.get_or_create(
            cliente_idcliente=client_profiles[0],
            fecha=date.today() + timedelta(days=1),
            defaults={
                'idreserva': self._next_id(Reserva, 'idreserva'),
                'hora_bloque': timezone.make_aware(
                    datetime.combine(date.today() + timedelta(days=1), time(12, 30))
                ),
                'direccion_visita': client_profiles[0].direccion_domicilio,
                'estado': 'Pendiente',
            },
        )
        reservation.servicios.set([services[0], services[1]])

        payment, _ = Pago.objects.get_or_create(
            reserva_idreserva=reservation,
            defaults={
                'idpago': self._next_id(Pago, 'idpago'),
                'monto_total': services[0].precio_base + services[1].precio_base,
                'metodo_pago': 'Webpay',
            },
        )

        for service in services:
            liquidation, _ = Liquidacion.objects.get_or_create(
                administrador_idadministrador=administrador,
                monto_bruto_total=service.precio_base,
                defaults={
                    'idliquidacion': self._next_id(Liquidacion, 'idliquidacion'),
                    'porcentaje_comision': 15.0,
                    'monto_comision_spa': round(service.precio_base * 0.15),
                    'monto_neto_prestador': round(service.precio_base * 0.85),
                },
            )
            ServicioHasLiquidacion.objects.get_or_create(
                servicio=service,
                liquidacion=liquidation,
            )

        self.stdout.write(self.style.SUCCESS(
            'Datos demo cargados. Usuarios demo: admin_demo, sofia.cliente, '
            'valentina.cliente y prestadores; contraseña: Demo12345!'
        ))

    @staticmethod
    def _user(username, email, first_name, last_name, password):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            },
        )
        changed = False
        if user.email != email:
            user.email = email
            changed = True
        if not user.first_name:
            user.first_name = first_name
            changed = True
        if not user.last_name:
            user.last_name = last_name
            changed = True
        if created:
            user.set_password(password)
            changed = True
        if changed:
            user.save()
        return user

    @staticmethod
    def _next_id(model, field_name):
        last = model.objects.order_by(f'-{field_name}').values_list(field_name, flat=True).first()
        return (last or 0) + 1

    @staticmethod
    def _existing_service_id(name, provider):
        service = Servicio.objects.filter(
            nombre=name,
            prestador_idprestador=provider,
        ).first()
        if service:
            return service.idservicio
        last = Servicio.objects.order_by('-idservicio').values_list('idservicio', flat=True).first()
        return (last or 0) + 1
