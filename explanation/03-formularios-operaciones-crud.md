# Formularios y operaciones CRUD

## Contexto de evaluación

Este documento cubre **A2. Formularios y creación de registros**, **A3.
Edición, eliminación y detalle**, **A5. Propiedad de los datos y permisos** y
**A7. Relaciones en listado y formularios**. El flujo principal está en
[`website/forms.py`](../website/forms.py),
[`website/views.py`](../website/views.py) y las plantillas de
[`templates/website/`](../templates/website/).

## Servicios: CRUD implementado

El CRUD de servicios pertenece al prestador aprobado y se concentra en
`vista_prestador`:

1. **Crear (POST)**: la acción `guardar_servicio` recibe `ServicioForm`,
   valida categoría, nombre, descripción, duración y precio, asigna el
   prestador autenticado y guarda el registro.
2. **Listar (GET)**: se consultan únicamente los servicios cuyo
   `prestador_idprestador` es el prestador actual. El listado se muestra en
   `vista_prestador.html`.
3. **Detalle (GET)**: `detalle_servicio/<id>/` usa `get_object_or_404`,
   `select_related` y exige que el prestador esté aprobado. La plantilla
   `detalle_servicio.html` muestra nombre, descripción, categoría, duración,
   precio, cobertura y prestador.
4. **Editar (GET + POST)**: el parámetro `editar` carga una instancia propia
   en el formulario; el POST vuelve a buscarla con el prestador autenticado
   antes de guardar.
5. **Eliminar (GET + POST)**: `eliminar` prepara una confirmación visual y el
   POST solo elimina si el servicio pertenece al prestador actual.

El formulario no permite editar el campo propietario: la vista lo fuerza con
`service.prestador_idprestador = prestador`. El estado aprobado se comprueba
antes de cualquier POST de administración del catálogo.

## Reservas

La vista `reservas` procesa la creación por `POST` desde el flujo de
agendamiento de `home`. Valida datos de contacto, fecha, hora y pago simulado;
crea el cliente si corresponde, crea `Reserva`, asocia el servicio por
`reservation.servicios.add(service)` y registra `Pago`, todo dentro de una
transacción.

El `GET` lista únicamente las reservas del perfil cliente autenticado. En el
panel de prestador, las reservas se listan cuando contienen servicios de ese
prestador y el prestador puede cambiar su estado a `Confirmada`, `Rechazada` o
`Completada`.

Esto es un CRUD parcial: existe creación, consulta y actualización de estado,
pero no hay formulario separado para editar/eliminar una reserva desde el
cliente. Esa ausencia debe declararse en la defensa en lugar de presentarla
como un CRUD completo.

## Suscripciones y liquidaciones

`SuscripcionPrestador` se crea o recupera para el período actual y cambia
entre `pendiente` y `pagada` desde el portal del prestador o el panel
administrativo. El modelo impide duplicar el período por prestador.

Las liquidaciones se consultan y filtran en el panel administrativo. El
proyecto muestra sus servicios asociados mediante la relación
`ServicioHasLiquidacion`, pero no presenta un formulario general de creación o
edición de liquidaciones.

## Propiedad y permisos

- Un prestador solo ve sus servicios porque el queryset filtra por su perfil.
- Editar y eliminar un ID de otro prestador produce `404` mediante
  `get_object_or_404`, sin modificar el registro ajeno.
- Cambiar una reserva exige que esta tenga un servicio del prestador
  autenticado.
- Un cliente ve sus propias reservas porque la consulta filtra por
  `cliente_idcliente`.
- El panel administrativo usa `admin_required` y permite superusuarios o
  perfiles `Administrador`.
- Ver el detalle de un servicio es público si el prestador está aprobado;
  reservar requiere autenticación y administrar requiere propiedad.

## Relaciones visibles y recomendaciones de `chat.json`

La base de datos sí contiene relaciones entre servicios, prestadores,
reservas, pagos y liquidaciones, pero el formulario de servicio solo muestra
la categoría como `choices`; no selecciona una entidad `Categoria` ni
etiquetas. Si el indicador A7 exige catálogo/etiquetas como tablas, deben
crearse esos modelos y conectarlos al formulario.

También se identificó trabajo pendiente para demostrar consultas eficientes:

- `vista_admin.html` usa `selected_provider.servicio_set.all`, por lo que la
  vista debería precargar esos servicios o establecer un `related_name`
  explícito.
- En `reservas`, el servicio y el pago se consultan dentro del ciclo; se
  recomienda `Prefetch` con el prestador/usuario y pagos precargados.
- El detalle podría mostrar reservas y liquidaciones asociadas para hacer
  visible el modelo relacional.

Estas son inclusiones recomendadas por el historial de
[`chat.json`](../chat.json); no se aplicaron porque la solicitud actual pide
documentación y prohíbe modificar código.

