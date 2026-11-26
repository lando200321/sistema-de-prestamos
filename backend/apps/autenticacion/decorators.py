from functools import wraps
from uuid import UUID

from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from .models import Usuario, RolPermiso, Sesion


# ==========================================
# VERIFICAR SESIÓN DEL USUARIO
# ==========================================

def sesion_requerida(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        usuario_id = request.session.get("usuario_id")

        if not usuario_id:
            return redirect("autenticacion:login")

        usuario = Usuario.objects.filter(
            id=usuario_id,
            activo=True,
            eliminado=False,
        ).first()

        if usuario is None or usuario.esta_bloqueado:

            request.session.flush()

            return redirect("autenticacion:login")

        sesion_id = request.session.get("seguridad_sesion_id")
        try:
            sesion_valida = sesion_id and Sesion.objects.filter(
                id=UUID(str(sesion_id)),
                usuario_id=usuario.id,
                fecha_cierre__isnull=True,
                fecha_expiracion__gt=timezone.now(),
            ).exists()
        except (TypeError, ValueError):
            sesion_valida = False

        if not sesion_valida:
            request.session.flush()
            return redirect("autenticacion:login")

        request.usuario_actual = usuario

        return view_func(request, *args, **kwargs)

    return wrapper


# ==========================================
# VERIFICAR PERMISOS DEL USUARIO
# ==========================================

def permiso_requerido(codigo_permiso):

    def decorator(view_func):

        @wraps(view_func)
        @sesion_requerida
        def wrapper(request, *args, **kwargs):

            usuario = request.usuario_actual

            tiene_permiso = RolPermiso.objects.filter(
                rol__usuarios_asignados__usuario_id=usuario.id,
                rol__activo=True,
                permiso__codigo=codigo_permiso
            ).exists()

            if not tiene_permiso:

                raise PermissionDenied(
                    "No tienes permisos para realizar esta acción."
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
