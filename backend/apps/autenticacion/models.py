from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone


class Usuario(models.Model):

    id = models.BigAutoField(primary_key=True)

    nombres = models.CharField(max_length=100)

    apellidos = models.CharField(max_length=100)

    documento = models.CharField(
        max_length=20,
        unique=True
    )

    correo = models.EmailField(
        max_length=150,
        unique=True
    )

    nombre_usuario = models.CharField(
        max_length=60,
        unique=True
    )

    password_hash = models.TextField()

    activo = models.BooleanField(default=True)

    intentos_fallidos = models.IntegerField(default=0)

    bloqueado_hasta = models.DateTimeField(
        null=True,
        blank=True
    )

    ultimo_acceso = models.DateTimeField(
        null=True,
        blank=True
    )

    fecha_creacion = models.DateTimeField(
        default=timezone.now
    )
    eliminado = models.BooleanField(
        default=False
    )

    fecha_eliminacion = models.DateTimeField(
        null=True,
        blank=True
    )

    eliminado_por = models.ForeignKey(
        "self",
        on_delete=models.DO_NOTHING,
        db_column="eliminado_por",
        null=True,
        blank=True,
        related_name="usuarios_eliminados"
    )

    class Meta:
        managed = False
        db_table = '"seguridad"."usuario"'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    def set_password(self, password):
        self.password_hash = make_password(password)

    def check_password(self, password):
        return check_password(password, self.password_hash)

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def esta_bloqueado(self):
        return (
            self.bloqueado_hasta is not None
            and self.bloqueado_hasta > timezone.now()
        )
# Create your models here.
# ==========================================
# MODELO ROL
# ==========================================

class Rol(models.Model):

    id = models.BigAutoField(primary_key=True)

    nombre = models.CharField(max_length=80)

    descripcion = models.TextField(
        null=True,
        blank=True
    )

    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = '"seguridad"."rol"'
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.nombre

# ==========================================
# MODELO PERMISO
# ==========================================

class Permiso(models.Model):

    id = models.BigAutoField(primary_key=True)

    codigo = models.CharField(max_length=80)

    modulo = models.CharField(max_length=10)

    descripcion = models.TextField()

    class Meta:
        managed = False
        db_table = '"seguridad"."permiso"'
        verbose_name = "Permiso"
        verbose_name_plural = "Permisos"

    def __str__(self):
        return self.codigo

# ==========================================
# MODELO USUARIO ROL
# ==========================================

class UsuarioRol(models.Model):

    pk = models.CompositePrimaryKey(
        "usuario_id",
        "rol_id"
    )

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.DO_NOTHING,
        db_column="usuario_id",
        related_name="roles_asignados"
    )

    rol = models.ForeignKey(
        Rol,
        on_delete=models.DO_NOTHING,
        db_column="rol_id",
        related_name="usuarios_asignados"
    )

    class Meta:
        managed = False
        db_table = '"seguridad"."usuario_rol"'
        verbose_name = "Usuario rol"
        verbose_name_plural = "Usuarios roles"

    def __str__(self):
        return f"{self.usuario} - {self.rol}"

# ==========================================
# MODELO ROL PERMISO
# ==========================================

class RolPermiso(models.Model):

    pk = models.CompositePrimaryKey(
        "rol_id",
        "permiso_id"
    )

    rol = models.ForeignKey(
        Rol,
        on_delete=models.DO_NOTHING,
        db_column="rol_id",
        related_name="permisos_asignados"
    )

    permiso = models.ForeignKey(
        Permiso,
        on_delete=models.DO_NOTHING,
        db_column="permiso_id",
        related_name="roles_asignados"
    )

    class Meta:
        managed = False
        db_table = '"seguridad"."rol_permiso"'
        verbose_name = "Rol permiso"
        verbose_name_plural = "Roles permisos"

    def __str__(self):
        return f"{self.rol} - {self.permiso}"


class Acceso(models.Model):
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.DO_NOTHING,
        db_column="usuario_id",
        null=True,
        blank=True,
        related_name="accesos_registrados",
    )
    nombre_usuario = models.CharField(max_length=60, null=True, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    exitoso = models.BooleanField()
    motivo = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = '"seguridad"."acceso"'
        ordering = ("-fecha", "-id")


class Sesion(models.Model):
    id = models.UUIDField(primary_key=True)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.DO_NOTHING,
        db_column="usuario_id",
        related_name="sesiones_seguridad",
    )
    token_hash = models.TextField()
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_expiracion = models.DateTimeField()
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '"seguridad"."sesion"'
        ordering = ("-fecha_inicio",)

    @property
    def vigente(self):
        return self.fecha_cierre is None and self.fecha_expiracion > timezone.now()


class Auditoria(models.Model):
    id = models.BigAutoField(primary_key=True)
    usuario_aplicacion_id = models.BigIntegerField(null=True, blank=True)
    usuario_bd = models.CharField(max_length=100)
    esquema = models.CharField(max_length=80)
    tabla = models.CharField(max_length=100)
    operacion = models.CharField(max_length=10)
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = '"cumplimiento"."auditoria"'
        ordering = ("-fecha", "-id")
