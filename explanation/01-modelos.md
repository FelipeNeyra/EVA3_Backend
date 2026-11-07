# Modelos y entidades

## Contexto de evaluación

Este documento explica el indicador **A1. Conexión y modelos (2.1.1)** del
Bloque A de la rúbrica. La aplicación usa Django ORM sobre MySQL, con la
configuración de la conexión en
[`gestion_citas_rgbeauty/settings.py`](../gestion_citas_rgbeauty/settings.py).
Las entidades y relaciones se definen en
[`website/models.py`](../website/models.py).

## Entidades principales

| Modelo                     | Propósito                                                | Relaciones relevantes                                                                                         |
| -------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `Cliente`                | Perfil de quien solicita servicios.                       | `OneToOneField` con `auth.User`; tiene muchas `Reserva`.                                                |
| `Prestador`              | Perfil profesional que ofrece servicios.                  | `OneToOneField` con `auth.User`; tiene muchos `Servicio` y `SuscripcionPrestador`.                    |
| `Administrador`          | Perfil que autoriza solicitudes y gestiona la operación. | `OneToOneField` con `auth.User`; participa en `Liquidacion` y registra suscripciones.                   |
| `Servicio`               | Catálogo de prestaciones publicadas.                     | `ForeignKey` a `Prestador`; relación M:N con `Reserva` y `Liquidacion` mediante modelos intermedios. |
| `Reserva`                | Agenda creada por un cliente para uno o más servicios.   | `ForeignKey` a `Cliente`; M:N con `Servicio` mediante `ReservaHasServicio`.                           |
| `ReservaHasServicio`     | Tabla intermedia de reservas y servicios.                 | Impone unicidad para no repetir el mismo servicio en una reserva.                                             |
| `Pago`                   | Abono asociado a una reserva.                             | `ForeignKey` a `Reserva`.                                                                                 |
| `Liquidacion`            | Montos bruto, comisión y neto de una liquidación.       | `ForeignKey` a `Administrador`; M:N con `Servicio`.                                                     |
| `ServicioHasLiquidacion` | Tabla intermedia entre servicios y liquidaciones.         | Impone unicidad de la pareja servicio/liquidación.                                                           |
| `SuscripcionPrestador`   | Suscripción mensual del prestador.                       | `ForeignKey` a `Prestador` y usuario que registra el pago; unicidad por período.                         |

## Claves y reglas del modelo

- Los perfiles se vinculan con el usuario de Django mediante `usuario`, por
  lo que autenticación y datos de negocio quedan separados.
- `on_delete=models.CASCADE` elimina los registros dependientes cuando la
  entidad propietaria desaparece; `SET_NULL` conserva una suscripción si se
  elimina el usuario que la registró.
- `Servicio.categoria` usa `choices`, mientras que duración y precio se
  validan principalmente en `ServicioForm`.
- Las restricciones `UniqueConstraint` protegen las tablas intermedias y
  evitan dos suscripciones del mismo prestador para el mismo mes.
- Los identificadores de `Reserva`, `Servicio`, `Pago` y `Liquidacion` son
  enteros explícitos. Las vistas calculan el siguiente valor disponible al
  crear ciertos registros.

## Cómo se usa el ORM

Las vistas consultan estas relaciones mediante filtros y carga anticipada:

- `_filtered_services` usa `select_related` para cargar prestador y usuario
  junto con cada servicio.
- `detalle_servicio` obtiene un servicio aprobado y su prestador.
- Las reservas usan `prefetch_related('servicios')`.
- Las relaciones de muchos a muchos se materializan con `reservation.servicios.add(service)`.

Esto permite explicar en la defensa la diferencia entre `ForeignKey`,
`OneToOneField`, `ManyToManyField` y un modelo intermedio.

## Observaciones para la rúbrica

La estructura relacional cumple la base de A1. Para demostrar mejor A7,
convendría hacer visibles en los listados el prestador del servicio, los
servicios de una reserva y las liquidaciones relacionadas. También sería
posible modelar un catálogo de `Categoria` y etiquetas con entidades propias
si la evaluación exige relaciones de catálogo, ya que actualmente la
categoría es un `choices` y no una tabla independiente. Estas son
recomendaciones del análisis registrado en [`chat.json`](../chat.json), no
modificaciones aplicadas.
