from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import (
    Administrador,
    Liquidacion,
    Prestador,
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
