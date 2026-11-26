from django.db import models
from django.utils import timezone


class Feriado(models.Model):
    fecha = models.DateField(primary_key=True)
    descripcion = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"catalogo"."feriado"'
        ordering = ("fecha",)


class FrecuenciaPago(models.Model):
    id = models.SmallAutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=60)
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    unidad = models.CharField(max_length=10)
    intervalo = models.SmallIntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"catalogo"."frecuencia_pago"'
        ordering = ("nombre",)


class MedioPago(models.Model):
    id = models.SmallAutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    requiere_referencia = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"catalogo"."medio_pago"'
        ordering = ("nombre",)


class Moneda(models.Model):
    codigo = models.CharField(max_length=3, primary_key=True)
    nombre = models.CharField(max_length=50)
    simbolo = models.CharField(max_length=10)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"catalogo"."moneda"'
        ordering = ("codigo",)


class TipoDocumento(models.Model):
    id = models.SmallAutoField(primary_key=True)
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"catalogo"."tipo_documento"'
        ordering = ("nombre",)


class TipoGarantia(models.Model):
    id = models.SmallAutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    naturaleza = models.CharField(max_length=15)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"catalogo"."tipo_garantia"'
        ordering = ("naturaleza", "nombre")


class Ubigeo(models.Model):
    codigo = models.CharField(max_length=6, primary_key=True)
    departamento = models.CharField(max_length=80)
    provincia = models.CharField(max_length=80)
    distrito = models.CharField(max_length=80)

    class Meta:
        managed = False
        db_table = '"catalogo"."ubigeo"'
        ordering = ("departamento", "provincia", "distrito")

    def __str__(self):
        return f"{self.departamento} / {self.provincia} / {self.distrito} ({self.codigo})"


class Empresa(models.Model):
    id = models.BigAutoField(primary_key=True)
    ruc = models.CharField(max_length=11, unique=True)
    razon_social = models.CharField(max_length=200)
    nombre_comercial = models.CharField(max_length=150, null=True, blank=True)
    direccion = models.CharField(max_length=250)
    ubigeo = models.ForeignKey(Ubigeo, models.DO_NOTHING, db_column="ubigeo_codigo", null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    correo = models.EmailField(max_length=150, null=True, blank=True)
    sitio_web = models.URLField(max_length=250, null=True, blank=True)
    logo = models.CharField(max_length=255, null=True, blank=True)
    representante_legal = models.CharField(max_length=200, null=True, blank=True)
    moneda = models.ForeignKey(Moneda, models.DO_NOTHING, db_column="moneda_codigo")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = '"configuracion"."empresa"'
        ordering = ("razon_social",)


class Sucursal(models.Model):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    ubigeo = models.ForeignKey(Ubigeo, models.DO_NOTHING, db_column="ubigeo_codigo", null=True, blank=True)
    activo = models.BooleanField(default=True)
    empresa = models.ForeignKey(Empresa, models.DO_NOTHING, db_column="empresa_id", null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"configuracion"."sucursal"'
        ordering = ("nombre",)


class TipoCambio(models.Model):
    id = models.BigAutoField(primary_key=True)
    moneda_origen = models.ForeignKey(Moneda, models.DO_NOTHING, db_column="moneda_origen", related_name="tipos_cambio_origen")
    moneda_destino = models.ForeignKey(Moneda, models.DO_NOTHING, db_column="moneda_destino", related_name="tipos_cambio_destino")
    fecha = models.DateField()
    tasa_compra = models.DecimalField(max_digits=18, decimal_places=8)
    tasa_venta = models.DecimalField(max_digits=18, decimal_places=8)
    fuente = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    registrado_por = models.ForeignKey("autenticacion.Usuario", models.DO_NOTHING, db_column="registrado_por")
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = '"configuracion"."tipo_cambio"'
        ordering = ("-fecha", "-id")


class Correlativo(models.Model):
    id = models.BigAutoField(primary_key=True)
    sucursal = models.ForeignKey(Sucursal, models.DO_NOTHING, db_column="sucursal_id")
    tipo_documento = models.CharField(max_length=50)
    serie = models.CharField(max_length=10)
    prefijo = models.CharField(max_length=15, null=True, blank=True)
    ultimo_numero = models.BigIntegerField(default=0)
    longitud = models.SmallIntegerField(default=8)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = '"configuracion"."correlativo"'
        ordering = ("sucursal__nombre", "tipo_documento", "serie")
        constraints = [models.UniqueConstraint(fields=("sucursal", "tipo_documento", "serie"), name="uq_correlativo")]

    def previsualizar_siguiente(self):
        from .services import CorrelativoService
        return CorrelativoService.formatear(self, self.ultimo_numero + 1)


class ParametroSistema(models.Model):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(null=True, blank=True)
    categoria = models.CharField(max_length=50)
    valor = models.JSONField()
    tipo_dato = models.CharField(max_length=20)
    editable = models.BooleanField(default=True)
    activo = models.BooleanField(default=True)
    actualizado_por = models.ForeignKey("autenticacion.Usuario", models.DO_NOTHING, db_column="actualizado_por", null=True, blank=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = '"configuracion"."parametro_sistema"'
        ordering = ("categoria", "codigo")


class ConceptoCobro(models.Model):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    fundamento = models.TextField()
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"configuracion"."concepto_cobro"'
        ordering = ("nombre",)


class LimiteInteres(models.Model):
    id = models.BigAutoField(primary_key=True)
    moneda = models.ForeignKey(Moneda, models.DO_NOTHING, db_column="moneda_codigo")
    regimen = models.CharField(max_length=80)
    tasa_compensatoria_maxima = models.DecimalField(max_digits=12, decimal_places=6)
    tasa_moratoria_maxima = models.DecimalField(max_digits=12, decimal_places=6)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    fuente_oficial = models.TextField()

    class Meta:
        managed = False
        db_table = '"configuracion"."limite_interes"'
        ordering = ("-vigente_desde",)


class ProductoCrediticio(models.Model):
    id = models.BigAutoField(primary_key=True)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    moneda = models.ForeignKey(Moneda, models.DO_NOTHING, db_column="moneda_codigo")
    monto_minimo = models.DecimalField(max_digits=18, decimal_places=2)
    monto_maximo = models.DecimalField(max_digits=18, decimal_places=2)
    plazo_minimo = models.IntegerField()
    plazo_maximo = models.IntegerField()
    porcentaje_financiamiento = models.DecimalField(max_digits=7, decimal_places=4)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"configuracion"."producto_crediticio"'
        ordering = ("nombre",)


class ProductoGarantia(models.Model):
    pk = models.CompositePrimaryKey("producto_id", "tipo_garantia_id")
    producto = models.ForeignKey(ProductoCrediticio, models.DO_NOTHING, db_column="producto_id")
    tipo_garantia = models.ForeignKey(TipoGarantia, models.DO_NOTHING, db_column="tipo_garantia_id")

    class Meta:
        managed = False
        db_table = '"configuracion"."producto_garantia"'


class ProductoFrecuencia(models.Model):
    pk = models.CompositePrimaryKey("producto_id", "frecuencia_pago_id")
    producto = models.ForeignKey(ProductoCrediticio, models.DO_NOTHING, db_column="producto_id")
    frecuencia_pago = models.ForeignKey(FrecuenciaPago, models.DO_NOTHING, db_column="frecuencia_pago_id")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = '"configuracion"."producto_frecuencia"'


class TasaInteres(models.Model):
    id = models.BigAutoField(primary_key=True)
    producto = models.ForeignKey(ProductoCrediticio, models.DO_NOTHING, db_column="producto_id")
    limite_interes = models.ForeignKey(LimiteInteres, models.DO_NOTHING, db_column="limite_interes_id")
    tea = models.DecimalField(max_digits=12, decimal_places=6)
    tasa_moratoria = models.DecimalField(max_digits=12, decimal_places=6)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"configuracion"."tasa_interes"'
        ordering = ("-vigente_desde",)


class PoliticaCrediticia(models.Model):
    id = models.BigAutoField(primary_key=True)
    producto = models.ForeignKey(ProductoCrediticio, models.DO_NOTHING, db_column="producto_id")
    version = models.IntegerField()
    condiciones = models.JSONField()
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    aprobado_por = models.ForeignKey("autenticacion.Usuario", models.DO_NOTHING, db_column="aprobado_por", null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"configuracion"."politica_crediticia"'
        ordering = ("producto__nombre", "-version")


class NivelAprobacion(models.Model):
    id = models.BigAutoField(primary_key=True)
    rol = models.ForeignKey("autenticacion.Rol", models.DO_NOTHING, db_column="rol_id")
    moneda = models.ForeignKey(Moneda, models.DO_NOTHING, db_column="moneda_codigo")
    monto_desde = models.DecimalField(max_digits=18, decimal_places=2)
    monto_hasta = models.DecimalField(max_digits=18, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"configuracion"."nivel_aprobacion"'
        ordering = ("moneda_id", "monto_desde")
