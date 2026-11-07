# Login y cuenta de usuario

## Contexto de evaluación

Este documento cubre **A4. Registro, inicio y cierre de sesión** y **A8.
Cuenta de usuario**. La autenticación se apoya en el usuario estándar de
Django; los perfiles `Cliente`, `Prestador` y `Administrador` se asocian a
ese usuario mediante relaciones uno a uno.

## Registro de cliente

La ruta `registro/` está declarada en
[`gestion_citas_rgbeauty/urls.py`](../gestion_citas_rgbeauty/urls.py). La vista
[`vista_registro`](../website/views.py) combina:

- `RegistroForm`, basado en `UserCreationForm`, para usuario, correo y
  contraseñas.
- `RegistroClienteForm` para nombre, dirección y teléfono.

En un `POST`, ambos formularios se validan. Si son válidos, una transacción
crea primero el usuario y luego el perfil `Cliente`, copia el correo de la
cuenta al perfil y ejecuta `login(request, user)`. Finalmente redirige a
`home`. En un `GET` solo se muestra el formulario.

La plantilla es
[`templates/website/usuario_formulario.html`](../templates/website/usuario_formulario.html)
y envía el formulario con `method="post"` y token CSRF.

## Inicio de sesión

La ruta `login/` usa `BeautyGoLoginView` y
`CorreoAuthenticationForm`. El formulario recibe un correo en el campo
`username`, busca el usuario por `email__iexact` y entrega el nombre de usuario
real al mecanismo de autenticación de Django.

Después de autenticarse:

- Un superusuario o usuario con perfil `Administrador` va a
  `vista_administrador`.
- Los demás usuarios siguen `LOGIN_REDIRECT_URL`, configurado como `home`.

La plantilla de login es
[`templates/website/login.html`](../templates/website/login.html). El cierre
de sesión usa `LogoutView` en `logout/` y se envía por `POST` desde la
plantilla base.

## Tipos de usuario

### Cliente

El registro público crea un `Cliente`. Puede consultar sus reservas, reservar
servicios y editar sus datos desde `home/datos_cuenta`. La vista
[`vista_editar_informacion_usuario`](../website/views.py) combina
`EditarUsuarioForm` con `RegistroClienteForm`, actualiza la cuenta y el perfil
en una transacción y muestra un mensaje de éxito.

### Prestador

No existe un registro público separado de credenciales para prestador. Un
cliente autenticado envía una solicitud mediante
`home/solicitudes`, usando `RegistroPrestadorForm`. La solicitud queda
asociada al usuario actual y con `estado_aprobacion` pendiente. Un
administrador la aprueba o rechaza desde el panel.

Una vez aprobado, el usuario accede a `prestador/`; si no tiene perfil
prestador, `vista_prestador` lanza `PermissionDenied`.

### Administrador

El administrador utiliza una cuenta Django existente vinculada a
`Administrador`, o un superusuario. El decorador `admin_required` exige login
y comprueba una de esas dos condiciones antes de permitir el panel, la
aprobación de prestadores y la gestión de suscripciones.

## Datos de cuenta y contraseña

- `home/datos_cuenta`: edición de usuario y perfil de cliente.
- `cambiar_contraseña/`: vista estándar `PasswordChangeView`.
- `cambiar_contraseña/hecho`: confirmación posterior al cambio.
- Las plantillas se encuentran en `templates/website/cuenta/`.

La barra de navegación cambia según `user.is_authenticated` y la existencia
de perfil prestador/administrador: muestra login y registro al visitante,
opciones de cuenta al cliente, portal al prestador y panel al administrador.

## Puntos a explicar en la defensa

Estar autenticado no equivale a tener permiso. `login_required` identifica al
usuario; `admin_required`, la comprobación del perfil prestador y los filtros
por propietario autorizan acciones concretas. Esta separación responde al
criterio 2.1.4 de la rúbrica.

