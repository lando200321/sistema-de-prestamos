from datetime import timedelta
from hashlib import sha256
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import connection
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import PermissionDenied
from .models import Acceso, Auditoria, Permiso, Rol, RolPermiso, Sesion, Usuario, UsuarioRol
from django.db import models


def _registrar_auditoria(administrador, tabla, operacion, anteriores=None, nuevos=None, direccion_ip=None):
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user")
        usuario_bd = cursor.fetchone()[0]
    Auditoria.objects.create(
        usuario_aplicacion_id=administrador.id if administrador else None,
        usuario_bd=usuario_bd,
        esquema="seguridad",
        tabla=tabla,
        operacion=operacion,
        datos_anteriores=anteriores,
        datos_nuevos=nuevos,
        direccion_ip=direccion_ip,
    )


def _cerrar_sesiones_usuario(usuario_id, ahora=None):
    ahora = ahora or timezone.now()
    Sesion.objects.filter(
        usuario_id=usuario_id,
        fecha_cierre__isnull=True,
    ).update(fecha_cierre=ahora)

    from django.contrib.sessions.models import Session
    keys = []
    for sesion in Session.objects.filter(expire_date__gt=ahora).iterator():
        try:
            if sesion.get_decoded().get("usuario_id") == usuario_id:
                keys.append(sesion.session_key)
        except (TypeError, ValueError):
            continue
    Session.objects.filter(session_key__in=keys).delete()

class AutenticacionService:

    MAX_INTENTOS = 5
    MINUTOS_BLOQUEO = 15

    @staticmethod
    @transaction.atomic
    def autenticar(nombre_usuario, password, direccion_ip=None):

        usuario = (
            Usuario.objects
            .select_for_update()
            .filter(nombre_usuario=nombre_usuario.strip(), eliminado=False)
            .first()
        )

        mensaje_error = "Credenciales incorrectas o acceso no disponible."
        ahora = timezone.now()

        if usuario is None:
            make_password(password)
            Acceso.objects.create(
                nombre_usuario=nombre_usuario.strip(), direccion_ip=direccion_ip,
                exitoso=False, motivo="CREDENCIALES_INVALIDAS", fecha=ahora,
            )
            return None, mensaje_error

        if not usuario.activo:
            Acceso.objects.create(
                usuario=usuario, nombre_usuario=usuario.nombre_usuario,
                direccion_ip=direccion_ip, exitoso=False,
                motivo="CUENTA_INACTIVA", fecha=ahora,
            )
            return None, mensaje_error

        if usuario.esta_bloqueado:
            Acceso.objects.create(
                usuario=usuario, nombre_usuario=usuario.nombre_usuario,
                direccion_ip=direccion_ip, exitoso=False,
                motivo="CUENTA_BLOQUEADA", fecha=ahora,
            )
            return None, mensaje_error

        # Restablecer intentos si el bloqueo ha terminado.
        if usuario.bloqueado_hasta is not None:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None

        # Validar contraseña.
        if not usuario.check_password(password):

            usuario.intentos_fallidos += 1

            if usuario.intentos_fallidos >= AutenticacionService.MAX_INTENTOS:

                usuario.bloqueado_hasta = ahora + timedelta(
                    minutes=AutenticacionService.MINUTOS_BLOQUEO
                )

            usuario.save(update_fields=[
                "intentos_fallidos",
                "bloqueado_hasta"
            ])

            Acceso.objects.create(
                usuario=usuario, nombre_usuario=usuario.nombre_usuario,
                direccion_ip=direccion_ip, exitoso=False,
                motivo="CREDENCIALES_INVALIDAS", fecha=ahora,
            )

            return None, mensaje_error

        # Autenticación correcta.
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.ultimo_acceso = ahora

        usuario.save(update_fields=[
            "intentos_fallidos",
            "bloqueado_hasta",
            "ultimo_acceso"
        ])

        Acceso.objects.create(
            usuario=usuario, nombre_usuario=usuario.nombre_usuario,
            direccion_ip=direccion_ip, exitoso=True,
            motivo="AUTENTICACION_EXITOSA", fecha=ahora,
        )

        return usuario, "Autenticación exitosa."
# ==========================================
# SERVICIO DE GESTIÓN DE USUARIOS
# ==========================================

@transaction.atomic
def registrar_sesion(usuario, clave_django, direccion_ip, segundos_vida):
    ahora = timezone.now()
    sesion_id = uuid4()
    Sesion.objects.create(
        id=sesion_id,
        usuario=usuario,
        token_hash=sha256(clave_django.encode("utf-8")).hexdigest(),
        direccion_ip=direccion_ip,
        fecha_inicio=ahora,
        fecha_expiracion=ahora + timedelta(seconds=segundos_vida),
        fecha_cierre=None,
    )
    _registrar_auditoria(
        usuario, "sesion", "INSERT", nuevos={"sesion_id": str(sesion_id)},
        direccion_ip=direccion_ip,
    )
    return sesion_id


@transaction.atomic
def cerrar_sesion_seguridad(sesion_id, administrador=None, direccion_ip=None):
    if not sesion_id:
        return False
    sesion = Sesion.objects.select_for_update().filter(
        id=sesion_id, fecha_cierre__isnull=True,
    ).first()
    if sesion is None:
        return False
    sesion.fecha_cierre = timezone.now()
    sesion.save(update_fields=["fecha_cierre"])
    _registrar_auditoria(
        administrador or sesion.usuario, "sesion", "UPDATE",
        anteriores={"estado": "ACTIVA"},
        nuevos={"estado": "CERRADA", "sesion_id": str(sesion.id)},
        direccion_ip=direccion_ip,
    )
    return True


@transaction.atomic
def revocar_sesion_seguridad(sesion_id, administrador, direccion_ip=None):
    sesion = Sesion.objects.select_for_update().filter(id=sesion_id).first()
    if sesion is None:
        raise Sesion.DoesNotExist
    if sesion.fecha_cierre is not None:
        return False
    ahora = timezone.now()
    sesion.fecha_cierre = ahora
    sesion.save(update_fields=["fecha_cierre"])
    from django.contrib.sessions.models import Session
    django_keys = []
    for django_session in Session.objects.filter(expire_date__gt=ahora).iterator():
        if sha256(django_session.session_key.encode("utf-8")).hexdigest() == sesion.token_hash:
            django_keys.append(django_session.session_key)
    Session.objects.filter(session_key__in=django_keys).delete()
    _registrar_auditoria(
        administrador, "sesion", "UPDATE",
        anteriores={"estado": "ACTIVA", "usuario_id": sesion.usuario_id},
        nuevos={"estado": "REVOCADA", "sesion_id": str(sesion.id)},
        direccion_ip=direccion_ip,
    )
    return True


class UsuarioService:

    @staticmethod
    @transaction.atomic
    def desbloquear_usuario(usuario_id, administrador, direccion_ip=None):
        usuario = Usuario.objects.select_for_update().get(id=usuario_id)
        if usuario.eliminado or not usuario.activo:
            raise ValidationError("La cuenta no está activa.")
        if not usuario.esta_bloqueado and usuario.intentos_fallidos == 0:
            raise ValidationError("La cuenta no está bloqueada.")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.usuario_id', %s, true)",
                [str(administrador.id)],
            )
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        _registrar_auditoria(
            administrador, "usuario", "UPDATE",
            anteriores={"estado": "BLOQUEADO"},
            nuevos={"estado": "DESBLOQUEADO", "usuario_id": usuario.id},
            direccion_ip=direccion_ip,
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def restablecer_password(usuario_id, password, administrador, direccion_ip=None):
        usuario = Usuario.objects.select_for_update().get(id=usuario_id)
        if usuario.eliminado:
            raise ValidationError("La cuenta fue eliminada.")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.usuario_id', %s, true)",
                [str(administrador.id)],
            )
        usuario.set_password(password)
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=[
            "password_hash", "intentos_fallidos", "bloqueado_hasta",
        ])
        _cerrar_sesiones_usuario(usuario.id)
        _registrar_auditoria(
            administrador, "usuario", "UPDATE",
            nuevos={"accion": "RESTABLECER_PASSWORD", "usuario_id": usuario.id},
            direccion_ip=direccion_ip,
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def modificar_roles(usuario_id, roles, administrador, direccion_ip=None):
        usuario = Usuario.objects.select_for_update().get(id=usuario_id)
        if usuario.eliminado:
            raise ValidationError("No se pueden asignar roles a una cuenta eliminada.")
        if usuario.id == administrador.id:
            raise ValidationError("Por separación de funciones no puedes modificar tus propios roles.")

        roles_ids = sorted({rol.id for rol in roles})
        roles_validos = list(Rol.objects.select_for_update().filter(
            id__in=roles_ids, activo=True,
        ).order_by("id"))
        if len(roles_validos) != len(roles_ids):
            raise ValidationError("Uno o más roles seleccionados ya no están activos.")

        roles_anteriores = list(UsuarioRol.objects.filter(
            usuario_id=usuario.id,
        ).values_list("rol_id", flat=True))
        tenia_admin = UsuarioRol.objects.filter(
            usuario_id=usuario.id,
            rol__nombre="ADMINISTRADOR",
            rol__activo=True,
        ).exists()
        tendra_admin = any(rol.nombre == "ADMINISTRADOR" for rol in roles_validos)
        if tenia_admin and not tendra_admin:
            otro_admin = Usuario.objects.filter(
                activo=True, eliminado=False,
                roles_asignados__rol__nombre="ADMINISTRADOR",
                roles_asignados__rol__activo=True,
            ).exclude(id=usuario.id).filter(
                models.Q(bloqueado_hasta__isnull=True)
                | models.Q(bloqueado_hasta__lte=timezone.now())
            ).exists()
            if not otro_admin:
                raise ValidationError("No puedes retirar el rol del último administrador disponible.")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.usuario_id', %s, true)",
                [str(administrador.id)],
            )
        UsuarioRol.objects.filter(usuario_id=usuario.id).delete()
        UsuarioRol.objects.bulk_create([
            UsuarioRol(usuario=usuario, rol=rol) for rol in roles_validos
        ])
        _registrar_auditoria(
            administrador, "usuario_rol", "UPDATE",
            anteriores={"usuario_id": usuario.id, "roles": roles_anteriores},
            nuevos={"usuario_id": usuario.id, "roles": roles_ids},
            direccion_ip=direccion_ip,
        )
        _cerrar_sesiones_usuario(usuario.id)
        return usuario

    @staticmethod
    @transaction.atomic
    def eliminar_usuario(usuario_id, administrador):

        usuario = Usuario.objects.select_for_update().get(id=usuario_id)

        if usuario.eliminado:
            raise ValidationError("La cuenta ya fue eliminada.")

        if usuario.id == administrador.id:
            raise ValidationError("No puedes eliminar tu propia cuenta.")

        es_administrador = UsuarioRol.objects.filter(
            usuario_id=usuario.id,
            rol__nombre="ADMINISTRADOR",
            rol__activo=True,
        ).exists()

        if es_administrador:
            administrador_disponible = Usuario.objects.filter(
                activo=True,
                eliminado=False,
                roles_asignados__rol__nombre="ADMINISTRADOR",
                roles_asignados__rol__activo=True,
            ).exclude(id=usuario.id).filter(
                models.Q(bloqueado_hasta__isnull=True)
                | models.Q(bloqueado_hasta__lte=timezone.now())
            ).exists()

            if not administrador_disponible:
                raise ValidationError(
                    "No puedes eliminar al último administrador disponible."
                )

        # Registrar al responsable. La transacción revierte también esta
        # operación si una relación histórica impide el borrado físico.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.usuario_id', %s, true)",
                [str(administrador.id)],
            )

        ahora = timezone.now()
        usuario.activo = False
        usuario.eliminado = True
        usuario.fecha_eliminacion = ahora
        usuario.eliminado_por = administrador
        usuario.bloqueado_hasta = None
        usuario.save(update_fields=[
            "activo", "eliminado", "fecha_eliminacion",
            "eliminado_por", "bloqueado_hasta",
        ])

        # Retirar sesiones autenticadas que todavía guarden este usuario.
        from django.contrib.sessions.models import Session

        session_keys = []
        sesiones = Session.objects.filter(expire_date__gt=timezone.now())
        for sesion in sesiones.iterator():
            if sesion.get_decoded().get("usuario_id") == usuario.id:
                session_keys.append(sesion.session_key)
        Session.objects.filter(session_key__in=session_keys).delete()
        Sesion.objects.filter(
            usuario_id=usuario.id, fecha_cierre__isnull=True,
        ).update(fecha_cierre=ahora)

        return usuario

    @staticmethod
    @transaction.atomic
    def crear_usuario(datos, administrador):

        roles_ids = [
            rol.id for rol in datos["roles"]
        ]

        roles = list(
            Rol.objects.select_for_update()
            .filter(id__in=roles_ids, activo=True)
            .order_by("id")
        )

        if not roles or len(roles) != len(roles_ids):

            raise ValidationError(
                "Los roles seleccionados no están disponibles."
            )

        # Identificar al responsable para auditoría
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT set_config('app.usuario_id', %s, true)",
                [str(administrador.id)]
            )

        usuario = Usuario(

            nombres=datos["nombres"].strip(),

            apellidos=datos["apellidos"].strip(),

            documento=datos["documento"].strip(),

            correo=datos["correo"].strip().lower(),

            nombre_usuario=datos["nombre_usuario"].strip(),

            activo=True,

            intentos_fallidos=0

        )

        # Generar hash seguro de la contraseña
        usuario.set_password(datos["password"])

        usuario.full_clean()

        usuario.save()

        # Asignar roles al usuario
        for rol in roles:

            UsuarioRol.objects.create(
                usuario=usuario,
                rol=rol
            )

        _registrar_auditoria(
            administrador, "usuario_rol", "INSERT",
            nuevos={"usuario_id": usuario.id, "roles": roles_ids},
        )

        return usuario
        # ==========================================
    # EDITAR USUARIO
    # ==========================================

    @staticmethod
    @transaction.atomic
    def editar_usuario(usuario_id, datos, administrador):

        usuario = Usuario.objects.select_for_update().get(
            id=usuario_id
        )

        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT set_config('app.usuario_id', %s, true)",
                [str(administrador.id)]
            )

        usuario.nombres = datos["nombres"].strip()

        usuario.apellidos = datos["apellidos"].strip()

        usuario.documento = datos["documento"].strip()

        usuario.correo = datos["correo"].strip().lower()

        usuario.nombre_usuario = datos["nombre_usuario"].strip()

        usuario.full_clean()

        usuario.save(update_fields=[
            "nombres",
            "apellidos",
            "documento",
            "correo",
            "nombre_usuario",
        ])

        return usuario
    # ==========================================
    # ACTIVAR Y DESACTIVAR USUARIO
    # ==========================================

    @staticmethod
    @transaction.atomic
    def cambiar_estado(usuario_id, activo, administrador):

        # Bloquear el rol administrador para serializar
        # los cambios de estado administrativos.
        Rol.objects.select_for_update().get(
            nombre="ADMINISTRADOR"
        )

        usuario = Usuario.objects.select_for_update().get(
            id=usuario_id
        )

        if usuario.eliminado:
            raise ValidationError("La cuenta fue eliminada y no admite cambios de estado.")

        if usuario.activo == activo:
            return usuario

        # Impedir la desactivación de la propia cuenta
        if not activo and usuario.id == administrador.id:

            raise ValidationError(
                "No puedes desactivar tu propia cuenta."
            )

        # Comprobar si el usuario es administrador
        es_administrador = UsuarioRol.objects.filter(
            usuario_id=usuario.id,
            rol__nombre="ADMINISTRADOR",
            rol__activo=True
        ).exists()

        if not activo and es_administrador:

            existe_otro_administrador = Usuario.objects.filter(
                activo=True,
                roles_asignados__rol__nombre="ADMINISTRADOR",
                roles_asignados__rol__activo=True
            ).exclude(
                id=usuario.id
            ).filter(
                models.Q(bloqueado_hasta__isnull=True) |
                models.Q(bloqueado_hasta__lte=timezone.now())
            ).exists()

            if not existe_otro_administrador:

                raise ValidationError(
                    "No puedes desactivar al último "
                    "administrador disponible."
                )

        # Registrar al responsable de la operación
        with connection.cursor() as cursor:

            cursor.execute(
                "SELECT set_config('app.usuario_id', %s, true)",
                [str(administrador.id)]
            )

        # Actualizar estado
        usuario.activo = activo

        usuario.save(update_fields=["activo"])

        if not activo:
            _cerrar_sesiones_usuario(usuario.id)

        # Invalidar las sesiones Django del usuario
        if not activo:

            from django.contrib.sessions.models import Session

            sesiones = Session.objects.filter(
                expire_date__gt=timezone.now()
            )

            sesiones_ids = []

            for sesion in sesiones.iterator():

                datos = sesion.get_decoded()

                if datos.get("usuario_id") == usuario.id:

                    sesiones_ids.append(sesion.session_key)

            Session.objects.filter(
                session_key__in=sesiones_ids
            ).delete()

        return usuario


class RolService:
    PERMISOS_ADMIN_MINIMOS = {
        "DASHBOARD_VER", "USUARIO_VER", "USUARIO_CREAR", "USUARIO_EDITAR",
        "USUARIO_ASIGNAR_ROL", "USUARIO_ACTIVAR", "USUARIO_DESACTIVAR",
        "USUARIO_ELIMINAR", "USUARIO_DESBLOQUEAR", "USUARIO_RESTABLECER_PASSWORD",
        "ROL_VER", "ROL_CREAR", "ROL_EDITAR", "ROL_ACTIVAR", "ROL_DESACTIVAR",
        "ROL_ELIMINAR", "ROL_ASIGNAR_PERMISO", "PERMISO_VER", "SESION_VER",
        "SESION_REVOCAR", "ACCESO_VER", "AUDITORIA_VER",
    }

    @staticmethod
    @transaction.atomic
    def crear(nombre, descripcion, administrador):
        nombre = " ".join(nombre.split()).upper()
        if Rol.objects.filter(nombre__iexact=nombre).exists():
            raise ValidationError("Ya existe un rol con ese nombre.")
        rol = Rol(nombre=nombre, descripcion=descripcion.strip())
        rol.full_clean()
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.usuario_id', %s, true)", [str(administrador.id)])
        rol.save()
        _registrar_auditoria(
            administrador, "rol", "INSERT",
            nuevos={"rol_id": rol.id, "nombre": rol.nombre},
        )
        return rol

    @staticmethod
    @transaction.atomic
    def editar(rol_id, nombre, descripcion, administrador):
        rol = Rol.objects.select_for_update().get(id=rol_id)
        if rol.nombre == "ADMINISTRADOR":
            raise ValidationError("El nombre del rol ADMINISTRADOR está reservado.")
        nuevo_nombre = " ".join(nombre.split()).upper()
        if Rol.objects.filter(nombre__iexact=nuevo_nombre).exclude(id=rol.id).exists():
            raise ValidationError("Ya existe un rol con ese nombre.")
        anterior = {"nombre": rol.nombre, "descripcion": rol.descripcion}
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.usuario_id', %s, true)", [str(administrador.id)])
        rol.nombre = nuevo_nombre
        rol.descripcion = descripcion.strip()
        rol.save(update_fields=["nombre", "descripcion"])
        _registrar_auditoria(
            administrador, "rol", "UPDATE", anteriores=anterior,
            nuevos={"rol_id": rol.id, "nombre": rol.nombre, "descripcion": rol.descripcion},
        )
        return rol

    @staticmethod
    @transaction.atomic
    def asignar_permisos(rol_id, permisos, administrador):
        rol = Rol.objects.select_for_update().get(id=rol_id)
        permisos_ids = sorted({permiso.id for permiso in permisos})
        permisos_validos = list(Permiso.objects.filter(id__in=permisos_ids).order_by("id"))
        if len(permisos_validos) != len(permisos_ids):
            raise ValidationError("La selección contiene permisos no disponibles.")
        codigos = {permiso.codigo for permiso in permisos_validos}
        if rol.nombre == "ADMINISTRADOR":
            faltantes = RolService.PERMISOS_ADMIN_MINIMOS - codigos
            if faltantes:
                raise ValidationError(
                    "No se pueden retirar permisos esenciales del rol Administrador."
                )
        anteriores = list(RolPermiso.objects.filter(
            rol_id=rol.id,
        ).values_list("permiso__codigo", flat=True))
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.usuario_id', %s, true)", [str(administrador.id)])
        RolPermiso.objects.filter(rol_id=rol.id).delete()
        RolPermiso.objects.bulk_create([
            RolPermiso(rol=rol, permiso=permiso) for permiso in permisos_validos
        ])
        _registrar_auditoria(
            administrador, "rol_permiso", "UPDATE",
            anteriores={"rol_id": rol.id, "permisos": anteriores},
            nuevos={"rol_id": rol.id, "permisos": sorted(codigos)},
        )
        return rol

    @staticmethod
    @transaction.atomic
    def cambiar_estado(rol_id, activo, administrador):
        rol = Rol.objects.select_for_update().get(id=rol_id)
        if rol.nombre == "ADMINISTRADOR" and not activo:
            raise ValidationError("El rol ADMINISTRADOR no se puede desactivar.")
        if rol.activo == activo:
            return rol
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.usuario_id', %s, true)", [str(administrador.id)])
        rol.activo = activo
        rol.save(update_fields=["activo"])
        _registrar_auditoria(
            administrador, "rol", "UPDATE",
            anteriores={"rol_id": rol.id, "activo": not activo},
            nuevos={"rol_id": rol.id, "activo": activo},
        )
        return rol

    @staticmethod
    @transaction.atomic
    def eliminar(rol_id, administrador):
        rol = Rol.objects.select_for_update().get(id=rol_id)
        if rol.nombre == "ADMINISTRADOR":
            raise ValidationError("El rol ADMINISTRADOR no se puede eliminar.")
        if UsuarioRol.objects.filter(rol_id=rol.id).exists():
            raise ValidationError("El rol tiene usuarios asignados. Desactívalo para conservar su historial.")
        permisos = list(RolPermiso.objects.filter(
            rol_id=rol.id,
        ).values_list("permiso__codigo", flat=True))
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.usuario_id', %s, true)", [str(administrador.id)])
        RolPermiso.objects.filter(rol_id=rol.id).delete()
        _registrar_auditoria(
            administrador, "rol", "DELETE",
            anteriores={"rol_id": rol.id, "nombre": rol.nombre, "permisos": permisos},
        )
        rol.delete()
