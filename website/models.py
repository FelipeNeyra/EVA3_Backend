from django.db import models
from django.conf import settings

class Cliente(models.Model):
    idcliente = models.AutoField(db_column='idCliente', primary_key=True)
    nombre = models.CharField(max_length=45, null=True, blank=True)
    correo = models.EmailField(
        max_length=254,
        unique=True,
        null=True,
        blank=True,
    )
    direccion_domicilio = models.CharField(max_length=45)
    telefono = models.CharField(max_length=12)
    nivel_acceso = models.CharField(
        max_length=10,
        default='cliente'
    )

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_cliente',
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.nombre or self.correo or f'Cliente {self.pk}'

    class Meta:
        db_table = 'cliente'


class Prestador(models.Model):
    idprestador = models.AutoField(db_column='idPrestador', primary_key=True)
    especialidad = models.CharField(max_length=45)
    id_certificacion_sanitaria = models.CharField(db_column='idCertificacion_Sanitaria', max_length=45)
    radio_cobertura = models.CharField(max_length=100)
    estado_aprobacion = models.BooleanField(default=False)
    nivel_acceso = models.CharField(
            max_length=10,
            default='prestador'
        )

    usuario = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.CASCADE,
            related_name='perfil_prestador',
            null=True,
            blank=True,
        )

    def __str__(self):
        return f'Prestador {self.pk}'

    class Meta:
        db_table = 'prestador'


class Administrador(models.Model):
    idadministrador = models.IntegerField(
        db_column='idAdministrador',
        primary_key=True)
    nombre = models.CharField(max_length=45)
    correo = models.CharField(max_length=45)
    contrasenia = models.CharField(max_length=10)
    telefono = models.CharField(max_length=12)
    nivel_acceso = models.CharField(max_length=10)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'administrador'


class Reserva(models.Model):
    idreserva = models.IntegerField(db_column='idReserva', primary_key=True)
    fecha = models.DateField()
    hora_bloque = models.DateTimeField()
    direccion_visita = models.CharField(max_length=45)
    estado = models.CharField(max_length=45)
    cliente_idcliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        db_column='cliente_idCliente')
    servicios = models.ManyToManyField(
        'Servicio',
        through='ReservaHasServicio',
        related_name='reservas')

    def __str__(self):
        return str(self.idreserva)

    class Meta:
        db_table = 'reserva'


class Servicio(models.Model):
    idservicio = models.IntegerField(db_column='idServicio', primary_key=True)
    nombre = models.CharField(max_length=45)
    duracion = models.IntegerField()
    precio_base = models.IntegerField()
    prestador_idprestador = models.ForeignKey(
        Prestador,
        on_delete=models.CASCADE,
        db_column='prestador_idPrestador')
    liquidaciones = models.ManyToManyField(
        'Liquidacion',
        through='ServicioHasLiquidacion',
        related_name='servicios')

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'servicio'


class ReservaHasServicio(models.Model):
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        db_column='reserva_idReserva')
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        db_column='servicio_idServicio')

    class Meta:
        db_table = 'reserva_has_servicio'
        constraints = [
            models.UniqueConstraint(
                fields=['reserva', 'servicio'],
                name='unique_reserva_servicio')
        ]


class Liquidacion(models.Model):
    idliquidacion = models.IntegerField(
        db_column='idLiquidacion',
        primary_key=True)
    monto_bruto_total = models.IntegerField()
    porcentaje_comision = models.FloatField()
    monto_comision_spa = models.IntegerField()
    monto_neto_prestador = models.IntegerField()
    administrador_idadministrador = models.ForeignKey(
        Administrador,
        on_delete=models.CASCADE,
        db_column='administrador_idAdministrador')

    def __str__(self):
        return str(self.idliquidacion)

    class Meta:
        db_table = 'liquidacion'


class ServicioHasLiquidacion(models.Model):
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        db_column='servicio_idServicio')
    liquidacion = models.ForeignKey(
        Liquidacion,
        on_delete=models.CASCADE,
        db_column='liquidacion_idLiquidacion')

    class Meta:
        db_table = 'servicio_has_liquidacion'
        constraints = [
            models.UniqueConstraint(
                fields=['servicio', 'liquidacion'],
                name='unique_servicio_liquidacion')
        ]


class Pago(models.Model):
    idpago = models.IntegerField(db_column='idPago', primary_key=True)
    monto_total = models.IntegerField()
    metodo_pago = models.CharField(max_length=45)
    reserva_idreserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        db_column='reserva_idReserva')

    def __str__(self):
        return str(self.idpago)

    class Meta:
        db_table = 'pago'
