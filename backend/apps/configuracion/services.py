import csv
import re
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal
from io import TextIOWrapper

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from apps.autenticacion.models import Auditoria
from . import models


@contextmanager
def contexto_auditoria(usuario):
    """La variable de auditoría vive solo en la transacción actual."""
    if usuario is None:
        raise ValidationError("No se pudo identificar al usuario responsable.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('app.usuario_id', %s, true)", [str(usuario.id)])
    yield


def _validar_ruc(ruc):
    if not re.fullmatch(r"\d{11}", ruc or ""):
        raise ValidationError({"ruc": "El RUC debe tener 11 dígitos."})
    digitos = [int(x) for x in ruc]
    factores = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    esperado = 11 - (sum(a * b for a, b in zip(digitos[:10], factores)) % 11)
    esperado = 0 if esperado == 10 else 1 if esperado == 11 else esperado
    if digitos[10] != esperado:
        raise ValidationError({"ruc": "El dígito verificador del RUC no es válido."})


class ConfiguracionService:
    @staticmethod
    @transaction.atomic
    def guardar(instancia, datos, usuario, archivo_logo=None):
        modelo = type(instancia)
        with contexto_auditoria(usuario):
            if isinstance(instancia, models.Empresa):
                _validar_ruc(datos.get("ruc", instancia.ruc))
                if archivo_logo:
                    from django.core.files.storage import default_storage
                    from django.utils.text import get_valid_filename
                    nombre = get_valid_filename(archivo_logo.name)
                    ruta = default_storage.save(f"empresa/logos/{nombre}", archivo_logo)
                    instancia.logo = ruta
            if isinstance(instancia, models.ParametroSistema):
                ParametroSistemaService.validar_valor(
                    datos.get("tipo_dato", instancia.tipo_dato),
                    datos.get("valor", instancia.valor),
                )
                codigo = datos.get("codigo", instancia.codigo).lower()
                if any(secret in codigo for secret in ("password", "token", "secret", "clave", "credential")):
                    raise ValidationError({"codigo": "No se permiten secretos ni credenciales como parámetros."})
                if not instancia._state.adding and not instancia.editable:
                    raise ValidationError("Este parámetro está marcado como no editable.")
            if isinstance(instancia, models.Correlativo) and not instancia._state.adding:
                datos.pop("ultimo_numero", None)
            if isinstance(instancia, models.PoliticaCrediticia):
                if not instancia._state.adding:
                    raise ValidationError("Las políticas registradas son inmutables; crea una nueva versión.")
                producto_politica = datos["producto"]
                condiciones = datos.get("condiciones")
                if not isinstance(condiciones, dict) or not condiciones:
                    raise ValidationError({"condiciones": "Registra condiciones como un objeto JSON no vacío."})
                desde_politica = datos["vigente_desde"]
                hasta_politica = datos.get("vigente_hasta")
                if hasta_politica and hasta_politica < desde_politica:
                    raise ValidationError({"vigente_hasta": "La fecha final no puede ser anterior a la inicial."})
                vigentes_previas = modelo.objects.select_for_update().filter(producto=producto_politica, vigente_desde__lt=desde_politica).filter(
                    Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=desde_politica)
                ).order_by("-vigente_desde")
                politica_previa = vigentes_previas.first()
                if politica_previa:
                    politica_previa.vigente_hasta = desde_politica - timedelta(days=1)
                    politica_previa.save(update_fields=["vigente_hasta"])
                periodo = modelo.objects.select_for_update().filter(producto=producto_politica, vigente_desde__lte=hasta_politica or date.max).filter(
                    Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=desde_politica)
                )
                if periodo.exists():
                    raise ValidationError("La vigencia se superpone con una política existente; registra fechas consecutivas.")
                ultimo = modelo.objects.select_for_update().filter(producto=producto_politica).order_by("-version").first()
                instancia.version = (ultimo.version + 1) if ultimo else 1
                instancia.aprobado_por = usuario
            if isinstance(instancia, models.TipoCambio) and instancia._state.adding:
                instancia.registrado_por = usuario
            if isinstance(instancia, models.ParametroSistema):
                instancia.actualizado_por = usuario
            if isinstance(instancia, models.ProductoCrediticio):
                if datos.get("monto_maximo", instancia.monto_maximo) < datos.get("monto_minimo", instancia.monto_minimo):
                    raise ValidationError({"monto_maximo": "El máximo debe ser igual o mayor que el mínimo."})
                if datos.get("plazo_maximo", instancia.plazo_maximo) < datos.get("plazo_minimo", instancia.plazo_minimo):
                    raise ValidationError({"plazo_maximo": "El plazo máximo debe ser igual o mayor que el mínimo."})
                porcentaje = datos.get("porcentaje_financiamiento", instancia.porcentaje_financiamiento)
                if porcentaje <= 0 or porcentaje > 100:
                    raise ValidationError({"porcentaje_financiamiento": "El porcentaje debe ser mayor que 0 y no superar 100 %."})
            if isinstance(instancia, models.NivelAprobacion):
                if datos.get("monto_hasta", instancia.monto_hasta) < datos.get("monto_desde", instancia.monto_desde):
                    raise ValidationError({"monto_hasta": "El monto hasta debe ser mayor o igual al monto desde."})
                rol = datos.get("rol") or getattr(instancia, "rol", None)
                if not rol.activo:
                    raise ValidationError({"rol": "No se puede asignar un rol inactivo a un nuevo nivel."})
                desde = datos.get("monto_desde", instancia.monto_desde)
                hasta = datos.get("monto_hasta", instancia.monto_hasta)
                moneda_nivel = datos.get("moneda") or getattr(instancia, "moneda", None)
                niveles = models.NivelAprobacion.objects.filter(rol=rol, moneda=moneda_nivel, activo=True, monto_desde__lte=hasta, monto_hasta__gte=desde)
                if instancia.pk:
                    niveles = niveles.exclude(pk=instancia.pk)
                if niveles.exists():
                    raise ValidationError("El rango se superpone con otro nivel activo del mismo rol y moneda.")
            if isinstance(instancia, (models.LimiteInteres, models.TasaInteres)):
                desde = datos.get("vigente_desde", instancia.vigente_desde)
                hasta = datos.get("vigente_hasta", instancia.vigente_hasta)
                if hasta and hasta < desde:
                    raise ValidationError({"vigente_hasta": "La fecha final no puede ser anterior a la inicial."})
                if isinstance(instancia, models.LimiteInteres):
                    moneda_limite = datos.get("moneda") or getattr(instancia, "moneda", None)
                    qs = modelo.objects.filter(moneda=moneda_limite, regimen=datos.get("regimen", instancia.regimen))
                    start, end = "vigente_desde", "vigente_hasta"
                else:
                    producto = datos.get("producto") or getattr(instancia, "producto", None)
                    limite = datos.get("limite_interes") or getattr(instancia, "limite_interes", None)
                    if producto.moneda_id != limite.moneda_id:
                        raise ValidationError({"limite_interes": "La moneda del límite debe coincidir con la del producto."})
                    qs = modelo.objects.filter(producto=producto)
                    start, end = "vigente_desde", "vigente_hasta"
                if instancia.pk:
                    qs = qs.exclude(pk=instancia.pk)
                hasta_efectivo = hasta or date.max
                qs = qs.filter(**{f"{start}__lte": hasta_efectivo}).filter(
                    Q(**{f"{end}__isnull": True}) | Q(**{f"{end}__gte": desde})
                )
                if qs.exists():
                    raise ValidationError("El periodo se superpone con otro registro vigente para la misma condición.")
                if isinstance(instancia, models.LimiteInteres) and models.TasaInteres.objects.filter(limite_interes=instancia).exists():
                    raise ValidationError("Este límite ya tiene tasas asociadas. Conserva el historial y registra un nuevo límite con otra fecha.")
                if isinstance(instancia, models.TasaInteres) and instancia.pk:
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT EXISTS (SELECT 1 FROM operaciones.prestamo WHERE tasa_interes_id = %s)', [instancia.pk])
                        tasa_en_uso = cursor.fetchone()[0]
                    if tasa_en_uso:
                        raise ValidationError("Esta tasa ya está asociada a préstamos. No se puede modificar históricamente.")
            if isinstance(instancia, models.ProductoCrediticio) and instancia.pk:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT EXISTS (SELECT 1 FROM creditos.solicitud WHERE producto_id = %s)', [instancia.pk])
                    producto_en_uso = cursor.fetchone()[0]
                if producto_en_uso:
                    campos_financieros = ("moneda", "monto_minimo", "monto_maximo", "plazo_minimo", "plazo_maximo", "porcentaje_financiamiento")
                    if any(campo in datos and datos[campo] != getattr(instancia, f"{campo}_id" if campo == "moneda" else campo) for campo in campos_financieros):
                        raise ValidationError("El producto ya tiene solicitudes asociadas. Los términos financieros históricos no se pueden cambiar.")
            for campo, valor in datos.items():
                if campo in {"id", "pk", "registrado_por", "aprobado_por", "actualizado_por", "version", "ultimo_numero"}:
                    continue
                if hasattr(instancia, campo):
                    setattr(instancia, campo, valor)
            instancia.full_clean()
            instancia.save()
            return instancia

    @staticmethod
    @transaction.atomic
    def cambiar_estado(instancia, activo, usuario):
        if not hasattr(instancia, "activo"):
            raise ValidationError("Este catálogo no admite activación o desactivación.")
        with contexto_auditoria(usuario):
            instancia = type(instancia).objects.select_for_update().get(pk=instancia.pk)
            if isinstance(instancia, models.ProductoCrediticio) and activo:
                tiene_garantias = models.ProductoGarantia.objects.filter(producto_id=instancia.pk, tipo_garantia__activo=True).exists()
                tiene_frecuencias = models.ProductoFrecuencia.objects.filter(producto_id=instancia.pk, activo=True, frecuencia_pago__activo=True).exists()
                tiene_tasa = models.TasaInteres.objects.filter(producto_id=instancia.pk, vigente_desde__lte=timezone.localdate()).filter(
                    Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=timezone.localdate())
                ).exists()
                tiene_politica = models.PoliticaCrediticia.objects.filter(producto_id=instancia.pk, vigente_desde__lte=timezone.localdate()).filter(
                    Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=timezone.localdate())
                ).exists()
                if not (tiene_garantias and tiene_frecuencias and tiene_tasa and tiene_politica):
                    raise ValidationError("Antes de activar, configura garantía, frecuencia, tasa y política vigentes.")
            instancia.activo = activo
            instancia.save(update_fields=["activo"])
            return instancia


class CorrelativoService:
    @staticmethod
    def formatear(correlativo, numero):
        numero = str(numero)
        if len(numero) > correlativo.longitud:
            raise ValidationError("El correlativo superó la longitud configurada; crea una nueva serie.")
        return f"{correlativo.prefijo or ''}{correlativo.serie}{numero.zfill(correlativo.longitud)}"

    @staticmethod
    @transaction.atomic
    def siguiente(correlativo_id, usuario):
        with contexto_auditoria(usuario):
            correlativo = models.Correlativo.objects.select_for_update().get(pk=correlativo_id, activo=True)
            nuevo = correlativo.ultimo_numero + 1
            codigo = CorrelativoService.formatear(correlativo, nuevo)
            correlativo.ultimo_numero = nuevo
            correlativo.fecha_actualizacion = timezone.now()
            correlativo.save(update_fields=["ultimo_numero", "fecha_actualizacion"])
            return codigo


class ParametroSistemaService:
    @staticmethod
    def validar_valor(tipo, valor):
        valido = {
            "TEXTO": isinstance(valor, str),
            "NUMERO": isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool),
            "BOOLEANO": isinstance(valor, bool),
            "JSON": isinstance(valor, (dict, list)),
        }.get(tipo, False)
        if not valido:
            raise ValidationError({"valor": "El valor no corresponde al tipo de dato seleccionado."})


class FeriadoService:
    @staticmethod
    def es_feriado(fecha):
        return models.Feriado.objects.filter(fecha=fecha, activo=True).exists()

    @staticmethod
    def es_dia_habil(fecha):
        return fecha.weekday() < 5 and not FeriadoService.es_feriado(fecha)

    @staticmethod
    def siguiente_dia_habil(fecha):
        while not FeriadoService.es_dia_habil(fecha):
            fecha += timedelta(days=1)
        return fecha


class ConfiguracionConsultaService:
    @staticmethod
    def frecuencias_habilitadas(producto_id):
        return models.FrecuenciaPago.objects.filter(
            activo=True,
            productofrecuencia__producto_id=producto_id,
            productofrecuencia__activo=True,
        ).order_by("intervalo", "nombre")

    @staticmethod
    def tipo_cambio_aplicable(moneda_origen, moneda_destino, fecha):
        return models.TipoCambio.objects.filter(
            moneda_origen_id=moneda_origen,
            moneda_destino_id=moneda_destino,
            fecha__lte=fecha,
            activo=True,
        ).order_by("-fecha", "-id").first()

    @staticmethod
    def parametro(codigo, predeterminado=None):
        try:
            parametro = models.ParametroSistema.objects.get(codigo=codigo, activo=True)
        except models.ParametroSistema.DoesNotExist:
            return predeterminado
        return parametro.valor


class ProductoRelacionesService:
    @staticmethod
    @transaction.atomic
    def actualizar(producto_id, garantias, frecuencias, usuario):
        with contexto_auditoria(usuario):
            producto = models.ProductoCrediticio.objects.select_for_update().get(pk=producto_id)
            garantias = list(garantias)
            frecuencias = list(frecuencias)
            if any(not item.activo for item in garantias):
                raise ValidationError("No se pueden asignar tipos de garantía inactivos.")
            if any(not item.activo for item in frecuencias):
                raise ValidationError("No se pueden asignar frecuencias inactivas.")
            asociaciones_actuales = set(models.ProductoGarantia.objects.filter(producto=producto).values_list("tipo_garantia_id", flat=True))
            asociaciones_nuevas = {item.id for item in garantias}
            if asociaciones_actuales != asociaciones_nuevas:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT EXISTS (SELECT 1 FROM creditos.solicitud WHERE producto_id = %s)', [producto.id])
                    producto_con_solicitudes = cursor.fetchone()[0]
                if producto_con_solicitudes:
                    raise ValidationError("El producto ya tiene solicitudes; no se pueden cambiar sus garantías históricas.")
                models.ProductoGarantia.objects.filter(producto=producto, tipo_garantia_id__in=asociaciones_actuales - asociaciones_nuevas).delete()
                modelos_nuevos = asociaciones_nuevas - asociaciones_actuales
                modelos_garantia = {item.id: item for item in garantias}
                models.ProductoGarantia.objects.bulk_create([
                    models.ProductoGarantia(producto=producto, tipo_garantia=modelos_garantia[item_id])
                    for item_id in modelos_nuevos
                ])
            existentes = {x.frecuencia_pago_id: x for x in models.ProductoFrecuencia.objects.filter(producto=producto)}
            ids = {x.id for x in frecuencias}
            for frecuencia_id, asociacion in existentes.items():
                asociacion.activo = frecuencia_id in ids
                asociacion.save(update_fields=["activo"])
            for frecuencia in frecuencias:
                if frecuencia.id not in existentes:
                    models.ProductoFrecuencia.objects.create(producto=producto, frecuencia_pago=frecuencia, activo=True)


class UbigeoImportService:
    CABECERAS = {"codigo", "departamento", "provincia", "distrito"}

    @staticmethod
    @transaction.atomic
    def importar(archivo, usuario, direccion_ip=None):
        if archivo.size > 5 * 1024 * 1024:
            raise ValidationError("El archivo supera el máximo permitido de 5 MB.")
        try:
            wrapper = TextIOWrapper(archivo.file, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(wrapper)
            if not reader.fieldnames or not UbigeoImportService.CABECERAS.issubset(set(reader.fieldnames)):
                raise ValidationError("El CSV debe incluir codigo, departamento, provincia y distrito.")
            nuevos, errores = [], []
            vistos = set()
            departamentos, provincias = {}, {}
            for numero, fila in enumerate(reader, start=2):
                codigo = (fila.get("codigo") or "").strip()
                departamento = (fila.get("departamento") or "").strip()
                provincia = (fila.get("provincia") or "").strip()
                distrito = (fila.get("distrito") or "").strip()
                if not re.fullmatch(r"\d{6}", codigo) or not all((departamento, provincia, distrito)):
                    errores.append(f"Fila {numero}: código o nombre inválido.")
                    continue
                if codigo in vistos:
                    errores.append(f"Fila {numero}: código duplicado dentro del archivo.")
                    continue
                prefijo_departamento, prefijo_provincia = codigo[:2], codigo[:4]
                if prefijo_departamento in departamentos and departamentos[prefijo_departamento] != departamento.casefold():
                    errores.append(f"Fila {numero}: el prefijo del departamento no coincide con las filas anteriores.")
                    continue
                if prefijo_provincia in provincias and provincias[prefijo_provincia] != (departamento.casefold(), provincia.casefold()):
                    errores.append(f"Fila {numero}: el prefijo de provincia no coincide con las filas anteriores.")
                    continue
                vistos.add(codigo)
                departamentos[prefijo_departamento] = departamento.casefold()
                provincias[prefijo_provincia] = (departamento.casefold(), provincia.casefold())
                nuevos.append(models.Ubigeo(codigo=codigo, departamento=departamento, provincia=provincia, distrito=distrito))
            if not nuevos:
                errores.append("El archivo no contiene filas válidas para importar.")
            if errores:
                raise ValidationError(errores[:20])
            existentes = set(models.Ubigeo.objects.filter(codigo__in=vistos).values_list("codigo", flat=True))
            if existentes:
                raise ValidationError(f"El archivo contiene {len(existentes)} códigos ya existentes; no se sobrescribió ningún dato.")
            with contexto_auditoria(usuario):
                models.Ubigeo.objects.bulk_create(nuevos, batch_size=500)
                Auditoria.objects.create(
                    usuario_aplicacion_id=usuario.id, usuario_bd="django",
                    esquema="catalogo", tabla="ubigeo", operacion="IMPORT",
                    datos_nuevos={"origen_archivo": archivo.name, "registros": len(nuevos), "resultado": "completado"},
                    direccion_ip=direccion_ip,
                )
            return len(nuevos)
        except UnicodeDecodeError as exc:
            raise ValidationError("El archivo debe tener codificación UTF-8.") from exc
