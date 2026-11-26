# Módulo 2: Configuración general

## Alcance implementado

El módulo usa las 20 tablas existentes en los esquemas `catalogo` y `configuracion`. Los modelos son `managed = False`; la aplicación no crea ni migra tablas.

- Panel con indicadores, alertas de configuración y cambios recientes, consultados desde PostgreSQL.
- Administración con búsqueda, filtro por estado, paginación, formularios y activación/desactivación de los catálogos editables.
- Empresa y sucursales; monedas, tipos de cambio, tipos de documento, medios de pago, tipos de garantía y Ubigeo.
- Feriados y frecuencias de pago, productos crediticios y sus asociaciones con frecuencias y garantías.
- Límites y tasas con verificación de vigencias y moneda; políticas como versiones inmutables; niveles de aprobación sin rangos superpuestos.
- Conceptos de cobro, correlativos internos bloqueados transaccionalmente y parámetros JSON tipados.
- Historial de auditoría de `catalogo` y `configuracion`, filtros y exportación CSV limitada a 10 000 filas.
- Selectores dependientes de departamento, provincia y distrito basados en el Ubigeo ya cargado. Importación CSV atómica, UTF-8, hasta 5 MB y sin sobrescribir códigos existentes.
- Acceso a vistas y acciones protegido con la sesión personalizada del Módulo 1 y permisos por acción.

## Puesta en marcha de permisos

El campo `seguridad.permiso.modulo` tiene longitud máxima 10; el script usa `CONFIG`. El archivo [configuracion_permisos.sql](../database/configuracion_permisos.sql) inserta 84 permisos y los asigna al rol `ADMINISTRADOR`, sin duplicados. Se ejecutó para corregir el acceso; verifiqué que el usuario `admin` tiene `CONFIGURACION_VER`. No se concedieron permisos a otros roles ni se tocaron datos financieros.

La aplicación no carga ni inventa feriados, tipos de cambio, límites, tasas, razones sociales, RUC, productos o datos de Ubigeo. Para usar el selector geográfico debe importarse un CSV basado en una fuente oficial, con columnas `codigo,departamento,provincia,distrito`.

## Auditoría y base existente

Se encontraron 20 tablas objetivo y 19 triggers de auditoría existentes, habilitados en `catalogo`/`configuracion` salvo Ubigeo. Las escrituras usan `app.usuario_id` en contexto transaccional para esos triggers; la importación registra su evento explícitamente. No se duplicaron triggers.

El esquema de préstamos no modela tablas ajenas al módulo en Django; donde se necesita proteger una tasa o producto ya referenciado, el servicio consulta PostgreSQL con SQL parametrizado. No hay una integración declarada para consultar SUNAT, SBS o BCRP. Las tablas sin campo `activo` (Ubigeo, límites, tasas y políticas versionadas) se conservan y no exponen eliminación.

## Verificaciones ejecutadas

- `python manage.py check`: correcto.
- `python manage.py test apps.configuracion`: 5 pruebas correctas; son pruebas aisladas sin escrituras a la base principal.
- No se generaron ni ejecutaron migraciones. `makemigrations --check --dry-run` detecta los modelos no administrados como cambios de estado por falta de una migración inicial; el comando se dejó en seco. No se debe aplicar ni generar una migración para estas tablas preexistentes.
- Se inspeccionaron metadatos PostgreSQL con transacción `READ ONLY`; no se agregaron ni actualizaron datos.

Las pruebas anteriores cubren construcción de formularios, compilación de plantillas, representación de tablas sin gestión ORM, validación JSON y formato/desbordamiento de correlativos. Aún hace falta la validación manual de flujos de escritura con credenciales de prueba y una base aislada. No se considera validada la integración de permisos hasta ejecutar el SQL revisado.
