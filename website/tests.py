from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Administrador,
    Cliente,
    Liquidacion,
    Pago,
    Prestador,
    Reserva,
    Servicio,
    ServicioHasLiquidacion,
    SuscripcionPrestador,
)


User = get_user_model()


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='panel-admin',
            email='admin@example.com',
            password='secure-test-password',
        )
        self.administrator = Administrador.objects.create(
            idadministrador=1,
            usuario=self.admin_user,
        )
        self.provider_user = User.objects.create_user(
            username='professional',
            email='professional@example.com',
            password='secure-test-password',
            first_name='Constanza',
            last_name='Ramirez',
        )
        self.provider = Prestador.objects.create(
            especialidad='Peluquería',
            numCertificacion_sanitaria='CERT-123',
            radio_cobertura='Copiapó',
            estado_aprobacion=None,
            usuario=self.provider_user,
        )

    def test_admin_login_redirects_to_dashboard(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin@example.com',
            'password': 'secure-test-password',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('vista_administrador'), response['Location'])

    def test_superuser_login_redirects_to_dashboard(self):
        User.objects.create_superuser(
            username='root-admin',
            email='root@example.com',
            password='secure-test-password',
        )

        response = self.client.post(reverse('login'), {
            'username': 'root@example.com',
            'password': 'secure-test-password',
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('vista_administrador'), response['Location'])

    def test_dashboard_requires_an_administrator(self):
        regular_user = User.objects.create_user(
            username='regular',
            password='secure-test-password',
        )
        self.client.force_login(regular_user)

        response = self.client.get(reverse('vista_administrador'))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_review_and_decide_on_applications(self):
        self.client.force_login(self.admin_user)
        dashboard = self.client.get(reverse('vista_administrador'))

        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'Constanza Ramirez')
        self.assertContains(dashboard, 'CERT-123')

        response = self.client.post(
            reverse('estado_solicitud', args=[self.provider.pk]),
            {'estado': 'True'},
        )

        self.provider.refresh_from_db()
        self.assertTrue(self.provider.estado_aprobacion)
        self.assertEqual(response.status_code, 302)

    def test_admin_can_register_and_revert_monthly_subscription_payment(self):
        self.client.force_login(self.admin_user)
        self.provider.estado_aprobacion = True
        self.provider.save(update_fields=['estado_aprobacion'])
        self.client.get(reverse('vista_administrador') + '?section=suscripciones')

        self.assertFalse(SuscripcionPrestador.objects.exists())

        response = self.client.post(
            reverse('actualizar_suscripcion', args=[self.provider.pk]),
            {'estado': SuscripcionPrestador.PAGADA},
        )
        subscription = SuscripcionPrestador.objects.get(prestador=self.provider)

        self.assertEqual(subscription.monto, 5000)
        self.assertEqual(subscription.estado, SuscripcionPrestador.PAGADA)
        self.assertIsNotNone(subscription.fecha_pago)
        self.assertEqual(subscription.registrado_por, self.admin_user)
        self.assertEqual(response.status_code, 302)

        self.client.post(
            reverse('actualizar_suscripcion', args=[self.provider.pk]),
            {'estado': SuscripcionPrestador.PENDIENTE},
        )
        subscription.refresh_from_db()
        self.assertEqual(subscription.estado, SuscripcionPrestador.PENDIENTE)
        self.assertIsNone(subscription.fecha_pago)

    def test_subscription_payment_cannot_be_changed_by_non_admin(self):
        regular_user = User.objects.create_user(
            username='regular',
            password='secure-test-password',
        )
        self.provider.estado_aprobacion = True
        self.provider.save(update_fields=['estado_aprobacion'])
        self.client.force_login(regular_user)

        response = self.client.post(
            reverse('actualizar_suscripcion', args=[self.provider.pk]),
            {'estado': SuscripcionPrestador.PAGADA},
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SuscripcionPrestador.objects.exists())

    def test_liquidations_are_visible_in_dashboard(self):
        self.client.force_login(self.admin_user)
        self.provider.estado_aprobacion = True
        self.provider.save(update_fields=['estado_aprobacion'])
        service = Servicio.objects.create(
            idservicio=1,
            nombre='Corte y brushing',
            duracion=90,
            precio_base=28000,
            prestador_idprestador=self.provider,
        )
        liquidation = Liquidacion.objects.create(
            idliquidacion=1,
            monto_bruto_total=28000,
            porcentaje_comision=15.0,
            monto_comision_spa=4200,
            monto_neto_prestador=23800,
            administrador_idadministrador=self.administrator,
        )
        ServicioHasLiquidacion.objects.create(
            servicio=service,
            liquidacion=liquidation,
        )

        response = self.client.get(
            reverse('vista_administrador') + '?section=liquidaciones'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Corte y brushing')
        self.assertContains(response, '$28.000')
        self.assertContains(response, '$23.800')


class ProviderDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='provider-client',
            email='provider@example.com',
            password='secure-test-password',
            first_name='Constanza',
            last_name='Ramirez',
        )
        self.client_profile = Cliente.objects.create(
            nombre='Constanza Ramirez',
            correo=self.user.email,
            direccion_domicilio='Copiapó',
            telefono='912345678',
            usuario=self.user,
        )
        self.provider = Prestador.objects.create(
            especialidad='Peluquería',
            numCertificacion_sanitaria='CERT-456',
            radio_cobertura='Copiapó',
            estado_aprobacion=True,
            usuario=self.user,
        )
        self.service = Servicio.objects.create(
            idservicio=5,
            nombre='Corte y brushing',
            duracion=90,
            precio_base=28000,
            prestador_idprestador=self.provider,
        )
        self.client.force_login(self.user)

    def test_provider_dashboard_shows_services_and_account_panel_link(self):
        response = self.client.get(reverse('vista_prestador'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tu perfil fue aprobado')
        self.assertContains(response, 'Corte y brushing')
        self.assertContains(response, 'Agregar dirección de atención')
        self.assertEqual(response.content.count(b'class="provider-role-link"'), 1)

    def test_provider_can_publish_and_edit_only_their_own_services(self):
        response = self.client.post(reverse('vista_prestador'), {
            'action': 'guardar_servicio',
            'categoria': 'Uñas',
            'nombre': 'Manicure permanente',
            'descripcion': 'Manicure permanente con nivelación y diseño sencillo.',
            'duracion': '60',
            'precio_base': '18000',
        })

        self.assertEqual(response.status_code, 302)
        created_service = Servicio.objects.get(nombre='Manicure permanente')
        self.assertEqual(created_service.prestador_idprestador, self.provider)
        self.assertEqual(created_service.idservicio, 6)
        self.assertEqual(created_service.categoria, 'Uñas')
        self.assertEqual(created_service.descripcion, 'Manicure permanente con nivelación y diseño sencillo.')

        response = self.client.post(reverse('vista_prestador'), {
            'action': 'guardar_servicio',
            'service_id': str(self.service.pk),
            'categoria': 'Peluquería',
            'nombre': 'Corte actualizado',
            'descripcion': 'Corte personalizado y brushing.',
            'duracion': '60',
            'precio_base': '30000',
        })

        self.assertEqual(response.status_code, 302)
        self.service.refresh_from_db()
        self.assertEqual(self.service.nombre, 'Corte actualizado')

    def test_service_fields_are_validated_before_publishing(self):
        response = self.client.post(reverse('vista_prestador'), {
            'action': 'guardar_servicio',
            'categoria': 'Categoría inválida',
            'nombre': '   ',
            'descripcion': '',
            'duracion': '75',
            'precio_base': '500',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Selecciona una categoría válida.')
        self.assertContains(response, 'Ingresa el nombre del servicio.')
        self.assertContains(response, 'Ingresa una descripción del servicio.')
        self.assertContains(response, 'Selecciona una duración válida.')
        self.assertContains(response, 'El precio mínimo es $1.000 CLP.')
        self.assertEqual(Servicio.objects.filter(
            prestador_idprestador=self.provider,
        ).count(), 1)

    def test_subscription_section_shows_current_status_and_payment_history(self):
        current_period = timezone.localdate().replace(day=1)
        previous_period = (
            current_period.replace(year=current_period.year - 1, month=12)
            if current_period.month == 1
            else current_period.replace(month=current_period.month - 1)
        )
        SuscripcionPrestador.objects.create(
            prestador=self.provider,
            periodo=previous_period,
            monto=5000,
            estado=SuscripcionPrestador.PAGADA,
            fecha_pago=timezone.now(),
        )

        response = self.client.get(
            reverse('vista_prestador') + '?section=suscripcion'
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Suscripción profesional')
        self.assertContains(response, 'Pago pendiente')
        self.assertContains(response, 'Pagar suscripción · $5.000')
        self.assertContains(response, 'Historial de mensualidades')
        self.assertContains(response, 'Pagos anteriores')
        self.assertContains(response, 'Pagada')

    def test_provider_can_simulate_current_month_subscription_payment_once(self):
        payment_url = reverse('vista_prestador') + '?section=suscripcion'
        response = self.client.post(reverse('vista_prestador'), {
            'action': 'pagar_suscripcion',
        })

        self.assertRedirects(response, payment_url)
        subscription = SuscripcionPrestador.objects.get(prestador=self.provider)
        self.assertEqual(subscription.periodo, timezone.localdate().replace(day=1))
        self.assertEqual(subscription.estado, SuscripcionPrestador.PAGADA)
        self.assertEqual(subscription.monto, 5000)
        self.assertIsNotNone(subscription.fecha_pago)
        self.assertEqual(subscription.registrado_por, self.user)

        payment_date = subscription.fecha_pago
        response = self.client.post(reverse('vista_prestador'), {
            'action': 'pagar_suscripcion',
        })

        self.assertRedirects(response, payment_url)
        self.assertEqual(
            SuscripcionPrestador.objects.filter(prestador=self.provider).count(),
            1,
        )
        subscription.refresh_from_db()
        self.assertEqual(subscription.fecha_pago, payment_date)

    def test_provider_can_manage_only_reservations_for_their_services(self):
        reservation = Reserva.objects.create(
            idreserva=10,
            fecha='2030-01-10',
            hora_bloque='2030-01-10T10:00:00Z',
            direccion_visita='Copiapó',
            estado='Pendiente',
            cliente_idcliente=self.client_profile,
        )
        reservation.servicios.add(self.service)

        response = self.client.get(reverse('vista_prestador') + '?section=reservas')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Corte y brushing')
        self.assertContains(response, 'Constanza Ramirez')

        response = self.client.post(reverse('vista_prestador'), {
            'action': 'actualizar_reserva',
            'reserva_id': str(reservation.pk),
            'estado': 'Confirmada',
        })

        self.assertEqual(response.status_code, 302)
        reservation.refresh_from_db()
        self.assertEqual(reservation.estado, 'Confirmada')

    def test_unapproved_provider_cannot_publish_services(self):
        self.provider.estado_aprobacion = None
        self.provider.save(update_fields=['estado_aprobacion'])

        response = self.client.post(reverse('vista_prestador'), {
            'action': 'guardar_servicio',
            'categoria': 'Peluquería',
            'nombre': 'Servicio pendiente',
            'descripcion': 'Servicio en espera de aprobación.',
            'duracion': '60',
            'precio_base': '10000',
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Servicio.objects.filter(nombre='Servicio pendiente').exists())

    def test_only_a_registered_client_can_apply_as_provider(self):
        new_user = User.objects.create_user(
            username='not-yet-client',
            email='new@example.com',
            password='secure-test-password',
        )
        self.client.force_login(new_user)

        response = self.client.get(reverse('solicitud_prestador'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('datos_usuario'))

    def test_registered_client_applies_using_the_same_account_and_email(self):
        new_user = User.objects.create_user(
            username='new-provider-client',
            email='new-provider@example.com',
            password='secure-test-password',
        )
        client_profile = Cliente.objects.create(
            nombre='Nuevo cliente',
            correo=new_user.email,
            direccion_domicilio='Copiapó',
            telefono='912345678',
            usuario=new_user,
        )
        self.client.force_login(new_user)

        response = self.client.post(reverse('solicitud_prestador'), {
            'especialidad': 'Uñas',
            'numCertificacion_sanitaria': 'CERT-NEW',
            'radio_cobertura': 'Copiapó',
        })

        self.assertEqual(response.status_code, 302)
        provider = Prestador.objects.get(usuario=new_user)
        self.assertEqual(provider.usuario.email, client_profile.correo)
        self.assertIsNone(provider.estado_aprobacion)


class PrivilegedBookingTests(TestCase):
    def test_administrator_can_open_the_catalog_to_book_a_service(self):
        admin_user = User.objects.create_user(
            username='catalog-admin',
            email='catalog-admin@example.com',
            password='secure-test-password',
        )
        Administrador.objects.create(idadministrador=3, usuario=admin_user)
        provider_user = User.objects.create_user(
            username='catalog-provider',
            email='catalog-provider@example.com',
        )
        provider = Prestador.objects.create(
            especialidad='Peluquería',
            numCertificacion_sanitaria='CERT-CATALOG',
            radio_cobertura='Copiapó',
            estado_aprobacion=True,
            usuario=provider_user,
        )
        Servicio.objects.create(
            idservicio=30,
            nombre='Corte disponible',
            duracion=60,
            precio_base=20000,
            prestador_idprestador=provider,
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-service-name="Corte disponible"')
        self.assertContains(response, 'Reservar')
        self.assertNotContains(response, 'Próximamente')
        self.assertContains(response, 'Panel admin')

    def test_registered_provider_can_open_booking_for_a_catalog_service(self):
        provider_user = User.objects.create_user(
            username='booking-provider',
            email='booking-provider@example.com',
        )
        Cliente.objects.create(
            nombre='Proveedor cliente',
            correo=provider_user.email,
            direccion_domicilio='Copiapó',
            telefono='912345678',
            usuario=provider_user,
        )
        Prestador.objects.create(
            especialidad='Uñas',
            numCertificacion_sanitaria='CERT-OWN',
            radio_cobertura='Copiapó',
            estado_aprobacion=True,
            usuario=provider_user,
        )
        service_provider_user = User.objects.create_user(
            username='other-booking-provider',
            email='other-booking-provider@example.com',
        )
        service_provider = Prestador.objects.create(
            especialidad='Faciales',
            numCertificacion_sanitaria='CERT-OTHER',
            radio_cobertura='Copiapó',
            estado_aprobacion=True,
            usuario=service_provider_user,
        )
        service = Servicio.objects.create(
            idservicio=31,
            nombre='Facial reservable',
            duracion=60,
            precio_base=25000,
            prestador_idprestador=service_provider,
        )
        self.client.force_login(provider_user)

        catalog = self.client.get(reverse('home'))

        self.assertEqual(catalog.status_code, 200)
        self.assertContains(catalog, 'data-service-name="Facial reservable"')
        self.assertContains(catalog, 'Reservar')
        self.assertNotContains(catalog, 'Próximamente')

        response = self.client.post(reverse('reservas'), {
            'service_id': str(service.pk),
            'date': '2030-01-10',
            'time': '10:00',
            'contact_name': 'Proveedor cliente',
            'contact_email': provider_user.email,
            'contact_phone': '912345678',
            'address': 'Copiapó',
            'payment_status': 'success',
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Reserva.objects.filter(
                cliente_idcliente__usuario=provider_user,
                servicios=service,
            ).exists()
        )

    def test_administrator_can_book_and_get_a_client_profile(self):
        admin_user = User.objects.create_user(
            username='booking-admin',
            email='booking-admin@example.com',
            password='secure-test-password',
        )
        Administrador.objects.create(idadministrador=2, usuario=admin_user)
        provider_user = User.objects.create_user(
            username='approved-provider',
            email='approved-provider@example.com',
        )
        provider = Prestador.objects.create(
            especialidad='Faciales',
            numCertificacion_sanitaria='CERT-789',
            radio_cobertura='Copiapó',
            estado_aprobacion=True,
            usuario=provider_user,
        )
        service = Servicio.objects.create(
            idservicio=1,
            nombre='Facial hidratación profunda',
            duracion=60,
            precio_base=32000,
            prestador_idprestador=provider,
        )
        self.client.force_login(admin_user)

        response = self.client.post(reverse('reservas'), {
            'service_id': str(service.pk),
            'date': '2030-01-10',
            'time': '10:00',
            'contact_name': 'Administración Beauty Go',
            'contact_email': admin_user.email,
            'contact_phone': '912345678',
            'address': 'Copiapó',
            'payment_status': 'success',
        })

        self.assertEqual(response.status_code, 302)
        client_profile = Cliente.objects.get(usuario=admin_user)
        reservation = Reserva.objects.get(cliente_idcliente=client_profile)
        self.assertEqual(reservation.servicios.get(), service)
        self.assertTrue(Pago.objects.filter(reserva_idreserva=reservation).exists())
