# Mensajes de resultado y navegación

## Contexto de evaluación

Este documento cubre **A9. Mensajes de resultado y navegación**. La rúbrica
espera que cada operación informe éxito o error y que el menú se adapte al
estado de sesión.

## Implementación de mensajes

Las vistas importan `django.contrib.messages` y publican mensajes antes de
redirigir. Algunos ejemplos son:

| Operación                                                       | Resultado comunicado                       |
| ---------------------------------------------------------------- | ------------------------------------------ |
| Reserva incompleta, correo/teléfono inválido o fecha inválida | `messages.error`.                        |
| Pago simulado rechazado                                          | `messages.error`; no se crea la reserva. |
| Registro de solicitud de prestador                               | `messages.success`.                      |
| Solicitud ya pendiente o rechazada                               | `messages.info`.                         |
| Servicio guardado                                                | `messages.success`.                      |
| Servicio eliminado                                               | `messages.success`.                      |
| Estado de reserva actualizado                                    | `messages.success`.                      |
| Suscripción ya pagada                                           | `messages.info`.                         |
| Pago de suscripción registrado                                  | `messages.success`.                      |
| Acción o estado no válido                                      | `messages.error`.                        |
| Aprobación/rechazo administrativa                               | `messages.success` o `messages.error`. |

Los formularios inválidos conservan el formulario y sus errores para que el
usuario corrija los datos. En el flujo de reserva, los errores redirigen a
`home`; en el formulario de servicio, la vista vuelve a renderizar la sección
con `service_form.errors`.

## Renderizado en la interfaz

[`templates/website/base.html`](../templates/website/base.html) contiene el
bloque global:

```django
{% if messages %}
  {% for message in messages %}
    <div class="message {{ message.tags }}">{{ message }}</div>
  {% endfor %}
{% endif %}
```

Al estar en la plantilla base, los avisos funcionan en home, reservas, portal
de prestador y panel administrativo. Los tags de Django permiten diferenciar
visualmente `success`, `error` e `info`.

## Navegación según sesión y rol

La misma plantilla base cambia el menú:

- Visitante: `Ingresar` y `Crear cuenta`.
- Cliente autenticado: agendamiento, reservas, favoritos, cuenta y salida.
- Prestador: portal, datos de cuenta y salida.
- Administrador: panel, sitio público y salida.

Las acciones mutables usan formularios `POST` con CSRF. El cierre de sesión
también usa `POST`, y la eliminación de servicios exige una segunda
confirmación visual.

## Ausencias y recomendaciones

La cobertura de mensajes es amplia, pero deben considerarse estas mejoras:

- La vista pública de detalle no muestra un mensaje propio cuando un servicio
  no existe o su prestador no está aprobado: `get_object_or_404` responde
  404. Puede ser correcto técnicamente, pero una página de error amigable
  mejoraría la navegación.
- La reserva crea un pago simulado y redirige con parámetros de confirmación;
  conviene conservar una confirmación visible y consistente si se modifica
  ese flujo.
- Las operaciones GET de preparar edición/eliminación no cambian datos y no
  necesitan mensaje; el éxito o error corresponde al POST.
- Si se incorporan las mejoras sugeridas en `chat.json` para reservas,
  relaciones visibles o permisos cruzados, cada rechazo debe emitir un
  mensaje explícito además del código HTTP correspondiente.

En conjunto, el proyecto cumple la expectativa principal de A9: informa los
resultados de los POST y centraliza su presentación, sin inventar éxito cuando
una validación o permiso falla.
