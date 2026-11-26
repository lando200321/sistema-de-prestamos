from datetime import timedelta

from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.autenticacion.models import Auditoria, RolPermiso
from . import models


RECURSOS = {
    "empresa": {"modelo": models.Empresa, "titulo": "Empresa", "permiso_ver": "EMPRESA_VER", "permiso_crear": "EMPRESA_CREAR", "permiso_editar": "EMPRESA_EDITAR", "prefijo_permiso": "EMPRESA", "campos": (("RUC", "ruc"), ("Razón social", "razon_social"), ("Nombre comercial", "nombre_comercial"), ("Moneda", "moneda"), ("Estado", "activo")), "busqueda": ("ruc", "razon_social", "nombre_comercial")},
    "sucursales": {"modelo": models.Sucursal, "titulo": "Sucursales", "permiso_ver": "SUCURSAL_VER", "permiso_crear": "SUCURSAL_CREAR", "permiso_editar": "SUCURSAL_EDITAR", "prefijo_permiso": "SUCURSAL", "campos": (("Código", "codigo"), ("Nombre", "nombre"), ("Empresa", "empresa"), ("Ubigeo", "ubigeo"), ("Estado", "activo")), "busqueda": ("codigo", "nombre", "direccion")},
    "monedas": {"modelo": models.Moneda, "titulo": "Monedas", "permiso_ver": "MONEDA_VER", "permiso_crear": "MONEDA_CREAR", "permiso_editar": "MONEDA_EDITAR", "prefijo_permiso": "MONEDA", "campos": (("Código", "codigo"), ("Nombre", "nombre"), ("Símbolo", "simbolo"), ("Estado", "activo")), "busqueda": ("codigo", "nombre")},
    "tipos-cambio": {"modelo": models.TipoCambio, "titulo": "Tipos de cambio", "permiso_ver": "TIPO_CAMBIO_VER", "permiso_crear": "TIPO_CAMBIO_CREAR", "permiso_editar": "TIPO_CAMBIO_EDITAR", "prefijo_permiso": "TIPO_CAMBIO", "campos": (("Fecha", "fecha"), ("Origen", "moneda_origen"), ("Destino", "moneda_destino"), ("Compra", "tasa_compra"), ("Venta", "tasa_venta"), ("Fuente", "fuente"), ("Estado", "activo")), "busqueda": ("fuente", "moneda_origen__codigo", "moneda_destino__codigo")},
    "tipos-documento": {"modelo": models.TipoDocumento, "titulo": "Tipos de documento", "permiso_ver": "TIPO_DOCUMENTO_VER", "permiso_crear": "TIPO_DOCUMENTO_CREAR", "permiso_editar": "TIPO_DOCUMENTO_EDITAR", "prefijo_permiso": "TIPO_DOCUMENTO", "campos": (("Código", "codigo"), ("Nombre", "nombre"), ("Estado", "activo")), "busqueda": ("codigo", "nombre")},
    "medios-pago": {"modelo": models.MedioPago, "titulo": "Medios de pago", "permiso_ver": "MEDIO_PAGO_VER", "permiso_crear": "MEDIO_PAGO_CREAR", "permiso_editar": "MEDIO_PAGO_EDITAR", "prefijo_permiso": "MEDIO_PAGO", "campos": (("Medio", "nombre"), ("Requiere referencia", "requiere_referencia"), ("Estado", "activo")), "busqueda": ("nombre",)},
    "tipos-garantia": {"modelo": models.TipoGarantia, "titulo": "Tipos de garantía", "permiso_ver": "TIPO_GARANTIA_VER", "permiso_crear": "TIPO_GARANTIA_CREAR", "permiso_editar": "TIPO_GARANTIA_EDITAR", "prefijo_permiso": "TIPO_GARANTIA", "campos": (("Código", "codigo"), ("Tipo", "nombre"), ("Naturaleza", "naturaleza"), ("Estado", "activo")), "busqueda": ("codigo", "nombre", "naturaleza")},
    "feriados": {"modelo": models.Feriado, "titulo": "Feriados y calendario laboral", "permiso_ver": "FERIADO_VER", "permiso_crear": "FERIADO_CREAR", "permiso_editar": "FERIADO_EDITAR", "prefijo_permiso": "FERIADO", "campos": (("Fecha", "fecha"), ("Descripción", "descripcion"), ("Estado", "activo")), "busqueda": ("descripcion",)},
    "frecuencias-pago": {"modelo": models.FrecuenciaPago, "titulo": "Frecuencias de pago", "permiso_ver": "FRECUENCIA_PAGO_VER", "permiso_crear": "FRECUENCIA_PAGO_CREAR", "permiso_editar": "FRECUENCIA_PAGO_EDITAR", "prefijo_permiso": "FRECUENCIA_PAGO", "campos": (("Código", "codigo"), ("Nombre", "nombre"), ("Unidad", "unidad"), ("Intervalo", "intervalo"), ("Estado", "activo")), "busqueda": ("codigo", "nombre", "unidad")},
    "productos": {"modelo": models.ProductoCrediticio, "titulo": "Productos crediticios", "permiso_ver": "PRODUCTO_CREDITICIO_VER", "permiso_crear": "PRODUCTO_CREDITICIO_CREAR", "permiso_editar": "PRODUCTO_CREDITICIO_EDITAR", "prefijo_permiso": "PRODUCTO_CREDITICIO", "campos": (("Código", "codigo"), ("Producto", "nombre"), ("Moneda", "moneda"), ("Rango de monto", "monto_minimo"), ("Plazos", "plazo_minimo"), ("Estado", "activo")), "busqueda": ("codigo", "nombre", "descripcion"), "relaciones": True},
    "limites-interes": {"modelo": models.LimiteInteres, "titulo": "Límites de interés", "permiso_ver": "LIMITE_INTERES_VER", "permiso_crear": "LIMITE_INTERES_CREAR", "permiso_editar": "LIMITE_INTERES_EDITAR", "prefijo_permiso": "LIMITE_INTERES", "campos": (("Moneda", "moneda"), ("Régimen", "regimen"), ("TEA máxima", "tasa_compensatoria_maxima"), ("Moratoria máxima", "tasa_moratoria_maxima"), ("Desde", "vigente_desde"), ("Hasta", "vigente_hasta")), "busqueda": ("regimen", "fuente_oficial")},
    "tasas-interes": {"modelo": models.TasaInteres, "titulo": "Tasas de interés", "permiso_ver": "TASA_INTERES_VER", "permiso_crear": "TASA_INTERES_CREAR", "permiso_editar": "TASA_INTERES_EDITAR", "prefijo_permiso": "TASA_INTERES", "campos": (("Producto", "producto"), ("TEA", "tea"), ("Moratoria", "tasa_moratoria"), ("Desde", "vigente_desde"), ("Hasta", "vigente_hasta")), "busqueda": ("producto__nombre",)},
    "politicas-crediticias": {"modelo": models.PoliticaCrediticia, "titulo": "Políticas crediticias", "permiso_ver": "POLITICA_CREDITICIA_VER", "permiso_crear": "POLITICA_CREDITICIA_CREAR", "permiso_editar": None, "campos": (("Producto", "producto"), ("Versión", "version"), ("Vigente desde", "vigente_desde"), ("Vigente hasta", "vigente_hasta")), "busqueda": ("producto__nombre",)},
    "niveles-aprobacion": {"modelo": models.NivelAprobacion, "titulo": "Niveles de aprobación", "permiso_ver": "NIVEL_APROBACION_VER", "permiso_crear": "NIVEL_APROBACION_CREAR", "permiso_editar": "NIVEL_APROBACION_EDITAR", "campos": (("Rol", "rol"), ("Moneda", "moneda"), ("Desde", "monto_desde"), ("Hasta", "monto_hasta"), ("Estado", "activo")), "busqueda": ()},
    "conceptos-cobro": {"modelo": models.ConceptoCobro, "titulo": "Conceptos de cobro", "permiso_ver": "CONCEPTO_COBRO_VER", "permiso_crear": "CONCEPTO_COBRO_CREAR", "permiso_editar": "CONCEPTO_COBRO_EDITAR", "prefijo_permiso": "CONCEPTO_COBRO", "campos": (("Código", "codigo"), ("Concepto", "nombre"), ("Fundamento", "fundamento"), ("Estado", "activo")), "busqueda": ("codigo", "nombre", "fundamento")},
    "correlativos": {"modelo": models.Correlativo, "titulo": "Correlativos internos", "permiso_ver": "CORRELATIVO_VER", "permiso_crear": "CORRELATIVO_CREAR", "permiso_editar": "CORRELATIVO_EDITAR", "prefijo_permiso": "CORRELATIVO", "campos": (("Sucursal", "sucursal"), ("Tipo", "tipo_documento"), ("Serie", "serie"), ("Prefijo", "prefijo"), ("Último número", "ultimo_numero"), ("Vista previa", "previsualizar_siguiente"), ("Estado", "activo")), "busqueda": ("tipo_documento", "serie", "prefijo")},
    "parametros": {"modelo": models.ParametroSistema, "titulo": "Parámetros del sistema", "permiso_ver": "PARAMETRO_SISTEMA_VER", "permiso_crear": "PARAMETRO_SISTEMA_CREAR", "permiso_editar": "PARAMETRO_SISTEMA_EDITAR", "prefijo_permiso": "PARAMETRO_SISTEMA", "campos": (("Código", "codigo"), ("Nombre", "nombre"), ("Categoría", "categoria"), ("Tipo", "tipo_dato"), ("Valor", "valor"), ("Editable", "editable"), ("Estado", "activo")), "busqueda": ("codigo", "nombre", "categoria", "descripcion")},
    "ubigeo": {"modelo": models.Ubigeo, "titulo": "Ubigeo", "permiso_ver": "UBIGEO_VER", "permiso_crear": None, "permiso_editar": None, "campos": (("Código", "codigo"), ("Departamento", "departamento"), ("Provincia", "provincia"), ("Distrito", "distrito")), "busqueda": ("codigo", "departamento", "provincia", "distrito")},
}


GRUPOS = (
    ("Configuración institucional", ("empresa", "sucursales")),
    ("Catálogos generales", ("monedas", "tipos-cambio", "tipos-documento", "medios-pago", "tipos-garantia", "ubigeo")),
    ("Productos crediticios", ("productos",)),
    ("Configuración financiera", ("limites-interes", "tasas-interes", "niveles-aprobacion", "conceptos-cobro", "correlativos")),
    ("Políticas crediticias", ("politicas-crediticias",)),
    ("Calendario laboral", ("feriados", "frecuencias-pago")),
    ("Parámetros operativos", ("parametros",)),
    ("Auditoría", ("auditoria",)),
)


def permisos_usuario(usuario):
    return set(RolPermiso.objects.filter(
        rol__usuarios_asignados__usuario_id=usuario.id,
        rol__activo=True,
    ).values_list("permiso__codigo", flat=True))


def resumen_panel(usuario):
    permisos = permisos_usuario(usuario)
    tarjetas = []
    for grupo, slugs in GRUPOS:
        enlaces = []
        for slug in slugs:
            if slug == "auditoria":
                codigo, titulo = "CONFIGURACION_AUDITORIA_VER", "Historial de configuración"
                url_name = "configuracion:auditoria"
            else:
                recurso = RECURSOS[slug]
                codigo, titulo = recurso["permiso_ver"], recurso["titulo"]
                url_name = f"configuracion:{slug.replace('-', '_')}"
            if codigo in permisos:
                enlaces.append({"titulo": titulo, "url_name": url_name})
        if enlaces:
            tarjetas.append({"grupo": grupo, "enlaces": enlaces})

    hoy = timezone.localdate()
    return {
        "tarjetas": tarjetas,
        "sucursales": models.Sucursal.objects.filter(activo=True).count(),
        "productos": models.ProductoCrediticio.objects.filter(activo=True).count(),
        "tasas_vigentes": models.TasaInteres.objects.filter(vigente_desde__lte=hoy).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=hoy)).count(),
        "politicas_vigentes": models.PoliticaCrediticia.objects.filter(vigente_desde__lte=hoy).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=hoy)).count(),
        "alertas": {
            "tasas_por_vencer": models.TasaInteres.objects.filter(vigente_hasta__range=(hoy, hoy + timedelta(days=30))).count(),
            "limites_por_vencer": models.LimiteInteres.objects.filter(vigente_hasta__range=(hoy, hoy + timedelta(days=30))).count(),
            "productos_incompletos": models.ProductoCrediticio.objects.filter(activo=True).exclude(pk__in=models.ProductoGarantia.objects.filter(tipo_garantia__activo=True).values("producto_id")).count(),
            "productos_sin_frecuencia": models.ProductoCrediticio.objects.filter(activo=True).exclude(pk__in=models.ProductoFrecuencia.objects.filter(activo=True, frecuencia_pago__activo=True).values("producto_id")).count(),
            "productos_sin_tasa": models.ProductoCrediticio.objects.filter(activo=True).exclude(pk__in=models.TasaInteres.objects.filter(vigente_desde__lte=hoy).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=hoy)).values("producto_id")).count(),
            "productos_sin_politica": models.ProductoCrediticio.objects.filter(activo=True).exclude(pk__in=models.PoliticaCrediticia.objects.filter(vigente_desde__lte=hoy).filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=hoy)).values("producto_id")).count(),
        },
        "cambios_recientes": Auditoria.objects.filter(esquema__in=("configuracion", "catalogo")).order_by("-fecha", "-id")[:5],
        "permisos": permisos,
    }


def listar_recurso(recurso, termino="", estado="", anio="", fecha="", moneda="", fuente=""):
    consulta = recurso["modelo"].objects.all()
    if recurso["modelo"] == models.TipoCambio:
        consulta = consulta.select_related("moneda_origen", "moneda_destino", "registrado_por")
    elif recurso["modelo"] == models.Empresa:
        consulta = consulta.select_related("moneda", "ubigeo")
    elif recurso["modelo"] == models.Sucursal:
        consulta = consulta.select_related("empresa", "ubigeo")
    elif recurso["modelo"] == models.NivelAprobacion:
        consulta = consulta.select_related("rol", "moneda")
    elif recurso["modelo"] == models.TasaInteres:
        consulta = consulta.select_related("producto", "limite_interes")
    elif recurso["modelo"] == models.LimiteInteres:
        consulta = consulta.select_related("moneda")
    elif recurso["modelo"] == models.PoliticaCrediticia:
        consulta = consulta.select_related("producto")
    elif recurso["modelo"] == models.Correlativo:
        consulta = consulta.select_related("sucursal")
    else:
        consulta = consulta.all()
    if termino:
        filtro = Q()
        for campo in recurso["busqueda"]:
            filtro |= Q(**{f"{campo}__icontains": termino})
        if filtro:
            consulta = consulta.filter(filtro)
    if estado in ("activo", "inactivo") and any(f.name == "activo" for f in recurso["modelo"]._meta.fields):
        consulta = consulta.filter(activo=(estado == "activo"))
    if recurso["modelo"] == models.Feriado and anio.isdigit():
        consulta = consulta.filter(fecha__year=int(anio))
    if recurso["modelo"] == models.TipoCambio:
        if fecha:
            consulta = consulta.filter(fecha=fecha)
        if moneda:
            consulta = consulta.filter(Q(moneda_origen_id=moneda) | Q(moneda_destino_id=moneda))
        if fuente:
            consulta = consulta.filter(fuente__icontains=fuente[:100])
    elif recurso["modelo"] == models.ProductoCrediticio and moneda:
        consulta = consulta.filter(moneda_id=moneda)
    elif recurso["modelo"] == models.TasaInteres and moneda:
        consulta = consulta.filter(producto__moneda_id=moneda)
    return consulta


def filas_para_tabla(registros, campos):
    filas = []
    for objeto in registros:
        celdas = []
        for etiqueta, ruta in campos:
            valor = objeto
            for componente in ruta.split("__"):
                valor = getattr(valor, componente, None) if valor is not None else None
            if callable(valor):
                try:
                    valor = valor()
                except ValidationError:
                    valor = "Longitud agotada; crea otra serie"
            celdas.append({"etiqueta": etiqueta, "valor": valor if valor not in (None, "") else "—"})
        filas.append({"objeto": objeto, "celdas": celdas})
    return filas
