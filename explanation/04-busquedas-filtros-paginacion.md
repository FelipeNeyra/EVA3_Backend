# Búsquedas, filtros y paginación

## Contexto de evaluación

Este documento explica **A6. Búsqueda, filtro y paginación** y parte de A7.
La rúbrica exige ordenar antes de paginar, buscar en varios campos, filtrar
por catálogo y conservar los parámetros al cambiar de página.

## Vista principal del cliente

La vista `home` obtiene los parámetros GET y delega el procesamiento en
`_filtered_services`:

- `q`: busca en categoría, nombre, descripción y nombre del prestador.
- `categoria`: filtra usando las categorías normalizadas.
- `prestador`: limita por el ID del prestador.
- `precio_min` y `precio_max`: filtran el precio base.
- `calificacion_min` y `calificacion_max`: filtran la calificación
  presentada por el catálogo.
- `orden`: permite nombre, precio o duración.

La consulta parte de servicios reales cuyos prestadores están aprobados y
vinculados a una cuenta. Después se aplican los filtros y se ordena la lista.
La función `_paginated_services` construye `Paginator` con seis elementos por
página y elimina solo `page` del querystring, conservando el resto de
parámetros.

[`templates/website/home.html`](../templates/website/home.html) presenta:

- Campo de búsqueda.
- Enlaces de categoría.
- Panel de rangos de precio y calificación.
- Selector de prestador y orden.
- Tarjetas de resultados.
- Enlaces anterior, siguiente y páginas numeradas.

Los enlaces incluyen `service_querystring`, por lo que una navegación como
`q=manicure&categoria=unas&orden=precio` mantiene búsqueda, filtro y orden.
Si no hay coincidencias, se muestra **“No hay registros disponibles”**.

## Vista del prestador

La sección `servicios` de `vista_prestador` aplica el mismo concepto, pero
sobre los servicios del prestador autenticado:

- búsqueda en nombre, descripción, categoría y especialidad;
- filtro por categoría;
- orden por nombre, precio o duración;
- seis servicios por página;
- querystring conservado en los controles de paginación.

La plantilla
[`templates/website/vista_prestador.html`](../templates/website/vista_prestador.html)
incluye el formulario de filtros y el listado del catálogo propio. Así se
demuestra que el usuario trabaja solo con sus registros.

## Relación con `chat.json`

El historial registra la corrección que eliminó el catálogo ficticio usado como
fallback, ajustó el mínimo de precio a `$1.000` y dejó la base de datos como
fuente única. También registra la incorporación de filtros GET, ordenamiento,
`Paginator` y pruebas para la vista de cliente y la del prestador.

Por tanto, el estado vacío actual es intencional: no significa que la vista
esté rota, sino que no existen servicios reales aprobados que cumplan los
filtros.

## Mejoras pendientes recomendadas

- Mantener pruebas explícitas para primera página, última página y combinación
  de todos los filtros.
- Verificar que un prestador no pueda consultar por URL servicios de otro
  desde el panel; el queryset actual ya restringe el listado, y los accesos
  directos de edición/eliminación usan propietario.
- Para una defensa más sólida, documentar que el ordenamiento ocurre antes de
  `Paginator`; paginar antes produciría páginas inconsistentes.
- Si se agregan entidades de catálogo y etiquetas, incorporar sus filtros al
  queryset y al formulario, no solo al texto renderizado.
