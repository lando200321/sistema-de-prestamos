BEGIN;
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM seguridad.rol WHERE UPPER(nombre) = 'ADMINISTRADOR' AND activo = TRUE) THEN
        RAISE EXCEPTION 'No se encontró el rol ADMINISTRADOR activo; no se aplicaron permisos.';
    END IF;
END; $$;
INSERT INTO seguridad.permiso (codigo, modulo, descripcion)
VALUES
    ('CONFIGURACION_VER', 'CONFIG', 'Permite configuracion ver en el módulo de configuración'),
    ('EMPRESA_VER', 'CONFIG', 'Permite empresa ver en el módulo de configuración'),
    ('EMPRESA_CREAR', 'CONFIG', 'Permite empresa crear en el módulo de configuración'),
    ('EMPRESA_EDITAR', 'CONFIG', 'Permite empresa editar en el módulo de configuración'),
    ('EMPRESA_ACTIVAR', 'CONFIG', 'Permite empresa activar en el módulo de configuración'),
    ('EMPRESA_DESACTIVAR', 'CONFIG', 'Permite empresa desactivar en el módulo de configuración'),
    ('SUCURSAL_VER', 'CONFIG', 'Permite sucursal ver en el módulo de configuración'),
    ('SUCURSAL_CREAR', 'CONFIG', 'Permite sucursal crear en el módulo de configuración'),
    ('SUCURSAL_EDITAR', 'CONFIG', 'Permite sucursal editar en el módulo de configuración'),
    ('SUCURSAL_ACTIVAR', 'CONFIG', 'Permite sucursal activar en el módulo de configuración'),
    ('SUCURSAL_DESACTIVAR', 'CONFIG', 'Permite sucursal desactivar en el módulo de configuración'),
    ('MONEDA_VER', 'CONFIG', 'Permite moneda ver en el módulo de configuración'),
    ('MONEDA_CREAR', 'CONFIG', 'Permite moneda crear en el módulo de configuración'),
    ('MONEDA_EDITAR', 'CONFIG', 'Permite moneda editar en el módulo de configuración'),
    ('MONEDA_ACTIVAR', 'CONFIG', 'Permite moneda activar en el módulo de configuración'),
    ('MONEDA_DESACTIVAR', 'CONFIG', 'Permite moneda desactivar en el módulo de configuración'),
    ('TIPO_CAMBIO_VER', 'CONFIG', 'Permite tipo cambio ver en el módulo de configuración'),
    ('TIPO_CAMBIO_CREAR', 'CONFIG', 'Permite tipo cambio crear en el módulo de configuración'),
    ('TIPO_CAMBIO_EDITAR', 'CONFIG', 'Permite tipo cambio editar en el módulo de configuración'),
    ('TIPO_CAMBIO_ACTIVAR', 'CONFIG', 'Permite tipo cambio activar en el módulo de configuración'),
    ('TIPO_CAMBIO_DESACTIVAR', 'CONFIG', 'Permite tipo cambio desactivar en el módulo de configuración'),
    ('TIPO_DOCUMENTO_VER', 'CONFIG', 'Permite tipo documento ver en el módulo de configuración'),
    ('TIPO_DOCUMENTO_CREAR', 'CONFIG', 'Permite tipo documento crear en el módulo de configuración'),
    ('TIPO_DOCUMENTO_EDITAR', 'CONFIG', 'Permite tipo documento editar en el módulo de configuración'),
    ('TIPO_DOCUMENTO_ACTIVAR', 'CONFIG', 'Permite tipo documento activar en el módulo de configuración'),
    ('TIPO_DOCUMENTO_DESACTIVAR', 'CONFIG', 'Permite tipo documento desactivar en el módulo de configuración'),
    ('MEDIO_PAGO_VER', 'CONFIG', 'Permite medio pago ver en el módulo de configuración'),
    ('MEDIO_PAGO_CREAR', 'CONFIG', 'Permite medio pago crear en el módulo de configuración'),
    ('MEDIO_PAGO_EDITAR', 'CONFIG', 'Permite medio pago editar en el módulo de configuración'),
    ('MEDIO_PAGO_ACTIVAR', 'CONFIG', 'Permite medio pago activar en el módulo de configuración'),
    ('MEDIO_PAGO_DESACTIVAR', 'CONFIG', 'Permite medio pago desactivar en el módulo de configuración'),
    ('TIPO_GARANTIA_VER', 'CONFIG', 'Permite tipo garantia ver en el módulo de configuración'),
    ('TIPO_GARANTIA_CREAR', 'CONFIG', 'Permite tipo garantia crear en el módulo de configuración'),
    ('TIPO_GARANTIA_EDITAR', 'CONFIG', 'Permite tipo garantia editar en el módulo de configuración'),
    ('TIPO_GARANTIA_ACTIVAR', 'CONFIG', 'Permite tipo garantia activar en el módulo de configuración'),
    ('TIPO_GARANTIA_DESACTIVAR', 'CONFIG', 'Permite tipo garantia desactivar en el módulo de configuración'),
    ('UBIGEO_VER', 'CONFIG', 'Permite ubigeo ver en el módulo de configuración'),
    ('UBIGEO_IMPORTAR', 'CONFIG', 'Permite ubigeo importar en el módulo de configuración'),
    ('FERIADO_VER', 'CONFIG', 'Permite feriado ver en el módulo de configuración'),
    ('FERIADO_CREAR', 'CONFIG', 'Permite feriado crear en el módulo de configuración'),
    ('FERIADO_EDITAR', 'CONFIG', 'Permite feriado editar en el módulo de configuración'),
    ('FERIADO_ACTIVAR', 'CONFIG', 'Permite feriado activar en el módulo de configuración'),
    ('FERIADO_DESACTIVAR', 'CONFIG', 'Permite feriado desactivar en el módulo de configuración'),
    ('FRECUENCIA_PAGO_VER', 'CONFIG', 'Permite frecuencia pago ver en el módulo de configuración'),
    ('FRECUENCIA_PAGO_CREAR', 'CONFIG', 'Permite frecuencia pago crear en el módulo de configuración'),
    ('FRECUENCIA_PAGO_EDITAR', 'CONFIG', 'Permite frecuencia pago editar en el módulo de configuración'),
    ('FRECUENCIA_PAGO_ACTIVAR', 'CONFIG', 'Permite frecuencia pago activar en el módulo de configuración'),
    ('FRECUENCIA_PAGO_DESACTIVAR', 'CONFIG', 'Permite frecuencia pago desactivar en el módulo de configuración'),
    ('PRODUCTO_CREDITICIO_VER', 'CONFIG', 'Permite producto crediticio ver en el módulo de configuración'),
    ('PRODUCTO_CREDITICIO_CREAR', 'CONFIG', 'Permite producto crediticio crear en el módulo de configuración'),
    ('PRODUCTO_CREDITICIO_EDITAR', 'CONFIG', 'Permite producto crediticio editar en el módulo de configuración'),
    ('PRODUCTO_CREDITICIO_ACTIVAR', 'CONFIG', 'Permite producto crediticio activar en el módulo de configuración'),
    ('PRODUCTO_CREDITICIO_DESACTIVAR', 'CONFIG', 'Permite producto crediticio desactivar en el módulo de configuración'),
    ('PRODUCTO_ASIGNAR_GARANTIA', 'CONFIG', 'Permite producto asignar garantia en el módulo de configuración'),
    ('PRODUCTO_ASIGNAR_FRECUENCIA', 'CONFIG', 'Permite producto asignar frecuencia en el módulo de configuración'),
    ('LIMITE_INTERES_VER', 'CONFIG', 'Permite limite interes ver en el módulo de configuración'),
    ('LIMITE_INTERES_CREAR', 'CONFIG', 'Permite limite interes crear en el módulo de configuración'),
    ('LIMITE_INTERES_EDITAR', 'CONFIG', 'Permite limite interes editar en el módulo de configuración'),
    ('TASA_INTERES_VER', 'CONFIG', 'Permite tasa interes ver en el módulo de configuración'),
    ('TASA_INTERES_CREAR', 'CONFIG', 'Permite tasa interes crear en el módulo de configuración'),
    ('TASA_INTERES_EDITAR', 'CONFIG', 'Permite tasa interes editar en el módulo de configuración'),
    ('POLITICA_CREDITICIA_VER', 'CONFIG', 'Permite politica crediticia ver en el módulo de configuración'),
    ('POLITICA_CREDITICIA_CREAR', 'CONFIG', 'Permite politica crediticia crear en el módulo de configuración'),
    ('POLITICA_CREDITICIA_VERSIONAR', 'CONFIG', 'Permite politica crediticia versionar en el módulo de configuración'),
    ('NIVEL_APROBACION_VER', 'CONFIG', 'Permite nivel aprobacion ver en el módulo de configuración'),
    ('NIVEL_APROBACION_CREAR', 'CONFIG', 'Permite nivel aprobacion crear en el módulo de configuración'),
    ('NIVEL_APROBACION_EDITAR', 'CONFIG', 'Permite nivel aprobacion editar en el módulo de configuración'),
    ('CONCEPTO_COBRO_VER', 'CONFIG', 'Permite concepto cobro ver en el módulo de configuración'),
    ('CONCEPTO_COBRO_CREAR', 'CONFIG', 'Permite concepto cobro crear en el módulo de configuración'),
    ('CONCEPTO_COBRO_EDITAR', 'CONFIG', 'Permite concepto cobro editar en el módulo de configuración'),
    ('CONCEPTO_COBRO_ACTIVAR', 'CONFIG', 'Permite concepto cobro activar en el módulo de configuración'),
    ('CONCEPTO_COBRO_DESACTIVAR', 'CONFIG', 'Permite concepto cobro desactivar en el módulo de configuración'),
    ('CORRELATIVO_VER', 'CONFIG', 'Permite correlativo ver en el módulo de configuración'),
    ('CORRELATIVO_CREAR', 'CONFIG', 'Permite correlativo crear en el módulo de configuración'),
    ('CORRELATIVO_EDITAR', 'CONFIG', 'Permite correlativo editar en el módulo de configuración'),
    ('CORRELATIVO_ACTIVAR', 'CONFIG', 'Permite correlativo activar en el módulo de configuración'),
    ('CORRELATIVO_DESACTIVAR', 'CONFIG', 'Permite correlativo desactivar en el módulo de configuración'),
    ('PARAMETRO_SISTEMA_VER', 'CONFIG', 'Permite parametro sistema ver en el módulo de configuración'),
    ('PARAMETRO_SISTEMA_CREAR', 'CONFIG', 'Permite parametro sistema crear en el módulo de configuración'),
    ('PARAMETRO_SISTEMA_EDITAR', 'CONFIG', 'Permite parametro sistema editar en el módulo de configuración'),
    ('PARAMETRO_SISTEMA_ACTIVAR', 'CONFIG', 'Permite parametro sistema activar en el módulo de configuración'),
    ('PARAMETRO_SISTEMA_DESACTIVAR', 'CONFIG', 'Permite parametro sistema desactivar en el módulo de configuración'),
    ('CONFIGURACION_AUDITORIA_VER', 'CONFIG', 'Permite configuracion auditoria ver en el módulo de configuración'),
    ('CONFIGURACION_EXPORTAR', 'CONFIG', 'Permite configuracion exportar en el módulo de configuración')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO seguridad.rol_permiso (rol_id, permiso_id)
SELECT r.id, p.id
FROM seguridad.rol AS r
CROSS JOIN seguridad.permiso AS p
WHERE UPPER(r.nombre) = 'ADMINISTRADOR' AND p.codigo IN ('CONFIGURACION_VER', 'EMPRESA_VER', 'EMPRESA_CREAR', 'EMPRESA_EDITAR', 'EMPRESA_ACTIVAR', 'EMPRESA_DESACTIVAR', 'SUCURSAL_VER', 'SUCURSAL_CREAR', 'SUCURSAL_EDITAR', 'SUCURSAL_ACTIVAR', 'SUCURSAL_DESACTIVAR', 'MONEDA_VER', 'MONEDA_CREAR', 'MONEDA_EDITAR', 'MONEDA_ACTIVAR', 'MONEDA_DESACTIVAR', 'TIPO_CAMBIO_VER', 'TIPO_CAMBIO_CREAR', 'TIPO_CAMBIO_EDITAR', 'TIPO_CAMBIO_ACTIVAR', 'TIPO_CAMBIO_DESACTIVAR', 'TIPO_DOCUMENTO_VER', 'TIPO_DOCUMENTO_CREAR', 'TIPO_DOCUMENTO_EDITAR', 'TIPO_DOCUMENTO_ACTIVAR', 'TIPO_DOCUMENTO_DESACTIVAR', 'MEDIO_PAGO_VER', 'MEDIO_PAGO_CREAR', 'MEDIO_PAGO_EDITAR', 'MEDIO_PAGO_ACTIVAR', 'MEDIO_PAGO_DESACTIVAR', 'TIPO_GARANTIA_VER', 'TIPO_GARANTIA_CREAR', 'TIPO_GARANTIA_EDITAR', 'TIPO_GARANTIA_ACTIVAR', 'TIPO_GARANTIA_DESACTIVAR', 'UBIGEO_VER', 'UBIGEO_IMPORTAR', 'FERIADO_VER', 'FERIADO_CREAR', 'FERIADO_EDITAR', 'FERIADO_ACTIVAR', 'FERIADO_DESACTIVAR', 'FRECUENCIA_PAGO_VER', 'FRECUENCIA_PAGO_CREAR', 'FRECUENCIA_PAGO_EDITAR', 'FRECUENCIA_PAGO_ACTIVAR', 'FRECUENCIA_PAGO_DESACTIVAR', 'PRODUCTO_CREDITICIO_VER', 'PRODUCTO_CREDITICIO_CREAR', 'PRODUCTO_CREDITICIO_EDITAR', 'PRODUCTO_CREDITICIO_ACTIVAR', 'PRODUCTO_CREDITICIO_DESACTIVAR', 'PRODUCTO_ASIGNAR_GARANTIA', 'PRODUCTO_ASIGNAR_FRECUENCIA', 'LIMITE_INTERES_VER', 'LIMITE_INTERES_CREAR', 'LIMITE_INTERES_EDITAR', 'TASA_INTERES_VER', 'TASA_INTERES_CREAR', 'TASA_INTERES_EDITAR', 'POLITICA_CREDITICIA_VER', 'POLITICA_CREDITICIA_CREAR', 'POLITICA_CREDITICIA_VERSIONAR', 'NIVEL_APROBACION_VER', 'NIVEL_APROBACION_CREAR', 'NIVEL_APROBACION_EDITAR', 'CONCEPTO_COBRO_VER', 'CONCEPTO_COBRO_CREAR', 'CONCEPTO_COBRO_EDITAR', 'CONCEPTO_COBRO_ACTIVAR', 'CONCEPTO_COBRO_DESACTIVAR', 'CORRELATIVO_VER', 'CORRELATIVO_CREAR', 'CORRELATIVO_EDITAR', 'CORRELATIVO_ACTIVAR', 'CORRELATIVO_DESACTIVAR', 'PARAMETRO_SISTEMA_VER', 'PARAMETRO_SISTEMA_CREAR', 'PARAMETRO_SISTEMA_EDITAR', 'PARAMETRO_SISTEMA_ACTIVAR', 'PARAMETRO_SISTEMA_DESACTIVAR', 'CONFIGURACION_AUDITORIA_VER', 'CONFIGURACION_EXPORTAR')
ON CONFLICT DO NOTHING;
COMMIT;





