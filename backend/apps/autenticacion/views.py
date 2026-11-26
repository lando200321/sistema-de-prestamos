from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from .forms import LoginForm
from .services import AutenticacionService
from .models import Usuario
from .selectors import DashboardSelector
from .decorators import permiso_requerido
from django.core.paginator import Paginator
from .selectors import UsuarioSelector
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from .forms import UsuarioCreacionForm
from .services import UsuarioService
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.http import Http404
from .forms import UsuarioEdicionForm
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Acceso, Auditoria, Permiso, Rol, RolPermiso, Sesion, UsuarioRol
from .forms import UsuarioRolesForm, UsuarioRestablecerPasswordForm, RolForm, RolPermisosForm
from .services import (
    RolService, registrar_sesion, cerrar_sesion_seguridad,
    revocar_sesion_seguridad,
)
from django.db.models import Count, IntegerField, OuterRef, Subquery, Value, Q
from django.db.models.functions import Coalesce
from datetime import timedelta
from uuid import UUID


def _direccion_ip(request):
    ip = request.META.get("REMOTE_ADDR")
    if not ip:
        return None
    try:
        from ipaddress import ip_address
        return str(ip_address(ip))
    except ValueError:
        return None

@never_cache
def iniciar_sesion(request):

    formulario = LoginForm()
    error = None

    if request.method == "POST":

        formulario = LoginForm(request.POST)

        if formulario.is_valid():

            usuario, mensaje = AutenticacionService.autenticar(
                formulario.cleaned_data["nombre_usuario"],
                formulario.cleaned_data["password"],
                direccion_ip=_direccion_ip(request),
            )

            if usuario is not None:

                request.session.flush()

                request.session["usuario_id"] = usuario.id
                request.session.save()
                sesion_id = registrar_sesion(
                    usuario=usuario,
                    clave_django=request.session.session_key,
                    direccion_ip=_direccion_ip(request),
                    segundos_vida=request.session.get_expiry_age(),
                )
                request.session["seguridad_sesion_id"] = str(sesion_id)
                request.session.save()

                return redirect("autenticacion:dashboard")

            error = mensaje

    return render(request, "autenticacion/login.html", {
        "formulario": formulario,
        "error": error
    })


@never_cache
@permiso_requerido("DASHBOARD_VER")
def dashboard(request):

    usuario_id = request.session.get("usuario_id")

    if not usuario_id:
        return redirect("autenticacion:login")

    usuario = Usuario.objects.filter(
        id=usuario_id,
        activo=True
    ).first()

    if usuario is None or usuario.esta_bloqueado:
        request.session.flush()
        return redirect("autenticacion:login")

    indicadores = DashboardSelector.obtener_indicadores()
    resumen = DashboardSelector.obtener_resumen_operaciones()

    contexto = {
        "usuario": usuario,
        "indicadores": indicadores,
        "resumen": resumen,
    }

    return render(
        request,
        "autenticacion/dashboard.html",
        contexto
    )


@require_POST
def cerrar_sesion(request):
    cerrar_sesion_seguridad(
        request.session.get("seguridad_sesion_id"),
        direccion_ip=_direccion_ip(request),
    )
    request.session.flush()

    return redirect("autenticacion:login")

# ==========================================
# MÓDULO DE USUARIOS Y ROLES
# ==========================================

@never_cache
@permiso_requerido("USUARIO_VER")
def usuarios(request):

    busqueda = request.GET.get("buscar", "").strip()
    estado = request.GET.get("estado", "")
    rol = request.GET.get("rol", "")

    listado = UsuarioSelector.listar_usuarios(
        busqueda=busqueda,
        estado=estado,
        rol=rol
    )

    paginador = Paginator(listado, 10)

    pagina = paginador.get_page(
        request.GET.get("pagina")
    )

    contexto = {
        "usuario": request.usuario_actual,
        "indicadores": UsuarioSelector.obtener_indicadores(),
        "usuarios": pagina,
        "roles": UsuarioSelector.listar_roles(),
        "busqueda": busqueda,
        "estado": estado,
        "rol_seleccionado": rol,
    }

    return render(
        request,
        "autenticacion/usuarios.html",
        contexto
    )
# ==========================================
# REGISTRAR NUEVO USUARIO
# ==========================================

@never_cache
@permiso_requerido("USUARIO_CREAR")
@permiso_requerido("USUARIO_ASIGNAR_ROL")
def usuario_crear(request):

    if request.method == "POST":

        formulario = UsuarioCreacionForm(request.POST)

        if formulario.is_valid():

            try:

                UsuarioService.crear_usuario(
                    datos=formulario.cleaned_data,
                    administrador=request.usuario_actual
                )

                return redirect("autenticacion:usuarios")

            except ValidationError as error:

                formulario.add_error(None, error)

            except IntegrityError:

                formulario.add_error(
                    None,
                    "No se pudo registrar el usuario. "
                    "Verifique que sus datos no estén duplicados."
                )

    else:

        formulario = UsuarioCreacionForm()

    contexto = {

        "usuario": request.usuario_actual,

        "formulario": formulario,

    }

    return render(
        request,
        "autenticacion/usuario_form.html",
        contexto
    )
# ==========================================
# EDITAR USUARIO
# ==========================================

@never_cache
@permiso_requerido("USUARIO_EDITAR")
@require_http_methods(["GET", "POST"])
def usuario_editar(request, usuario_id):

    usuario_editar = get_object_or_404(
        Usuario,
        id=usuario_id
    )

    if request.method == "POST":

        formulario = UsuarioEdicionForm(
            request.POST,
            instance=usuario_editar
        )

        if formulario.is_valid():

            try:

                UsuarioService.editar_usuario(
                    usuario_id=usuario_editar.id,
                    datos=formulario.cleaned_data,
                    administrador=request.usuario_actual
                )

                return redirect("autenticacion:usuarios")

            except Usuario.DoesNotExist:

                raise Http404("El usuario ya no existe.")

            except ValidationError as error:

                formulario.add_error(None, error)

            except IntegrityError:

                formulario.add_error(
                    None,
                    "No se pudieron guardar los cambios. "
                    "Verifique que los datos no estén duplicados."
                )

    else:

        formulario = UsuarioEdicionForm(
            instance=usuario_editar
        )

    contexto = {

        "usuario": request.usuario_actual,

        "usuario_editar": usuario_editar,

        "formulario": formulario,

    }

    return render(
        request,
        "autenticacion/usuario_editar.html",
        contexto
    )
# ==========================================
# ACTIVAR USUARIO
# ==========================================

@never_cache
@require_POST
@permiso_requerido("USUARIO_ACTIVAR")
def usuario_activar(request, usuario_id):

    try:

        usuario = UsuarioService.cambiar_estado(
            usuario_id=usuario_id,
            activo=True,
            administrador=request.usuario_actual
        )

        messages.success(
            request,
            f"El usuario {usuario.nombre_completo} "
            "ha sido activado correctamente."
        )

    except Usuario.DoesNotExist:

        raise Http404("El usuario no existe.")

    except ValidationError as error:

        messages.error(
            request,
            " ".join(error.messages)
        )

    return redirect("autenticacion:usuarios")


# ==========================================
# DESACTIVAR USUARIO
# ==========================================

@never_cache
@require_POST
@permiso_requerido("USUARIO_DESACTIVAR")
def usuario_desactivar(request, usuario_id):

    try:

        usuario = UsuarioService.cambiar_estado(
            usuario_id=usuario_id,
            activo=False,
            administrador=request.usuario_actual
        )

        messages.success(
            request,
            f"El usuario {usuario.nombre_completo} "
            "ha sido desactivado correctamente."
        )

    except Usuario.DoesNotExist:

        raise Http404("El usuario no existe.")

    except ValidationError as error:

        messages.error(
            request,
            " ".join(error.messages)
        )

    return redirect("autenticacion:usuarios")


@never_cache
@require_POST
@permiso_requerido("USUARIO_DESBLOQUEAR")
def usuario_desbloquear(request, usuario_id):
    try:
        usuario = UsuarioService.desbloquear_usuario(
            usuario_id, request.usuario_actual, _direccion_ip(request)
        )
        messages.success(request, f"La cuenta de {usuario.nombre_completo} fue desbloqueada.")
    except Usuario.DoesNotExist:
        raise Http404("El usuario no existe.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    return redirect("autenticacion:usuarios")


@never_cache
@require_http_methods(["GET", "POST"])
@permiso_requerido("USUARIO_RESTABLECER_PASSWORD")
def usuario_restablecer_password(request, usuario_id):
    usuario_objetivo = get_object_or_404(Usuario, id=usuario_id, eliminado=False)
    formulario = UsuarioRestablecerPasswordForm(
        request.POST or None, usuario=usuario_objetivo
    )
    if request.method == "POST" and formulario.is_valid():
        try:
            UsuarioService.restablecer_password(
                usuario_id, formulario.cleaned_data["password"],
                request.usuario_actual, _direccion_ip(request),
            )
            messages.success(request, "La contraseña se restableció y las sesiones anteriores se cerraron.")
            return redirect("autenticacion:usuarios")
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "autenticacion/usuario_password.html", {
        "usuario": request.usuario_actual,
        "usuario_objetivo": usuario_objetivo,
        "formulario": formulario,
    })


@never_cache
@require_http_methods(["GET", "POST"])
@permiso_requerido("USUARIO_ASIGNAR_ROL")
def usuario_roles(request, usuario_id):
    usuario_objetivo = get_object_or_404(Usuario, id=usuario_id, eliminado=False)
    roles_actuales = Rol.objects.filter(usuarios_asignados__usuario_id=usuario_id)
    formulario = UsuarioRolesForm(
        request.POST or None,
        initial={"roles": roles_actuales},
    )
    if request.method == "POST" and formulario.is_valid():
        try:
            UsuarioService.modificar_roles(
                usuario_id, formulario.cleaned_data["roles"],
                request.usuario_actual, _direccion_ip(request),
            )
            messages.success(request, "Los roles del usuario fueron actualizados.")
            return redirect("autenticacion:usuarios")
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "autenticacion/usuario_roles.html", {
        "usuario": request.usuario_actual,
        "usuario_objetivo": usuario_objetivo,
        "formulario": formulario,
    })


# ==========================================
# ELIMINAR USUARIO
# ==========================================

@never_cache
@require_POST
@permiso_requerido("USUARIO_ELIMINAR")
def usuario_eliminar(request, usuario_id):

    try:
        usuario = UsuarioService.eliminar_usuario(
            usuario_id=usuario_id,
            administrador=request.usuario_actual,
        )
        messages.success(
            request,
            f"La cuenta de {usuario.nombre_completo} fue eliminada.",
        )
    except Usuario.DoesNotExist:
        raise Http404("El usuario no existe.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    except IntegrityError:
        messages.error(
            request,
            "No se pudo dar de baja la cuenta. Revisa el historial asociado "
            "o contacta al administrador de base de datos.",
        )

    return redirect("autenticacion:usuarios")


@never_cache
@permiso_requerido("ROL_VER")
def roles(request):
    usuarios_por_rol = (
        UsuarioRol.objects.filter(
            rol_id=OuterRef("pk"),
            usuario__eliminado=False,
        )
        .values("rol_id")
        .annotate(total=Count("usuario_id"))
        .values("total")[:1]
    )
    permisos_por_rol = (
        RolPermiso.objects.filter(rol_id=OuterRef("pk"))
        .values("rol_id")
        .annotate(total=Count("permiso_id"))
        .values("total")[:1]
    )
    listado = Rol.objects.annotate(
        cantidad_usuarios=Coalesce(
            Subquery(usuarios_por_rol, output_field=IntegerField()), Value(0)
        ),
        cantidad_permisos=Coalesce(
            Subquery(permisos_por_rol, output_field=IntegerField()), Value(0)
        ),
    ).order_by("nombre")
    return render(request, "autenticacion/roles.html", {
        "usuario": request.usuario_actual,
        "roles": listado,
    })


@never_cache
@require_http_methods(["GET", "POST"])
@permiso_requerido("ROL_CREAR")
def rol_crear(request):
    formulario = RolForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        try:
            RolService.crear(
                formulario.cleaned_data["nombre"],
                formulario.cleaned_data["descripcion"] or "",
                request.usuario_actual,
            )
            messages.success(request, "El rol fue creado. Asigna sus permisos antes de habilitarlo para usuarios.")
            return redirect("autenticacion:roles")
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "autenticacion/rol_form.html", {
        "usuario": request.usuario_actual,
        "formulario": formulario,
        "titulo": "Crear rol",
    })


@never_cache
@require_http_methods(["GET", "POST"])
@permiso_requerido("ROL_EDITAR")
def rol_editar(request, rol_id):
    rol = get_object_or_404(Rol, id=rol_id)
    formulario = RolForm(request.POST or None, instance=rol)
    if request.method == "POST" and formulario.is_valid():
        try:
            RolService.editar(
                rol.id, formulario.cleaned_data["nombre"],
                formulario.cleaned_data["descripcion"] or "",
                request.usuario_actual,
            )
            messages.success(request, "Los datos del rol fueron actualizados.")
            return redirect("autenticacion:roles")
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "autenticacion/rol_form.html", {
        "usuario": request.usuario_actual,
        "formulario": formulario,
        "titulo": "Editar rol",
        "rol": rol,
    })


@never_cache
@require_http_methods(["GET", "POST"])
@permiso_requerido("ROL_ASIGNAR_PERMISO")
def rol_permisos(request, rol_id):
    rol = get_object_or_404(Rol, id=rol_id)
    asignados = Permiso.objects.filter(roles_asignados__rol_id=rol.id)
    formulario = RolPermisosForm(request.POST or None, initial={"permisos": asignados})
    if request.method == "POST" and formulario.is_valid():
        try:
            RolService.asignar_permisos(
                rol.id, formulario.cleaned_data["permisos"], request.usuario_actual,
            )
            messages.success(request, "Los permisos del rol fueron actualizados.")
            return redirect("autenticacion:roles")
        except ValidationError as error:
            formulario.add_error(None, error)
    return render(request, "autenticacion/rol_permisos.html", {
        "usuario": request.usuario_actual,
        "rol": rol,
        "formulario": formulario,
    })


@never_cache
@require_POST
@permiso_requerido("ROL_ACTIVAR")
def rol_activar(request, rol_id):
    try:
        RolService.cambiar_estado(rol_id, True, request.usuario_actual)
        messages.success(request, "El rol fue activado.")
    except Rol.DoesNotExist:
        raise Http404("El rol no existe.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    return redirect("autenticacion:roles")


@never_cache
@require_POST
@permiso_requerido("ROL_DESACTIVAR")
def rol_desactivar(request, rol_id):
    try:
        RolService.cambiar_estado(rol_id, False, request.usuario_actual)
        messages.success(request, "El rol fue desactivado; sus asignaciones e historial se conservan.")
    except Rol.DoesNotExist:
        raise Http404("El rol no existe.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    return redirect("autenticacion:roles")


@never_cache
@require_POST
@permiso_requerido("ROL_ELIMINAR")
def rol_eliminar(request, rol_id):
    try:
        RolService.eliminar(rol_id, request.usuario_actual)
        messages.success(request, "El rol fue eliminado.")
    except Rol.DoesNotExist:
        raise Http404("El rol no existe.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    except IntegrityError:
        messages.error(request, "No se puede eliminar este rol porque tiene registros asociados.")
    return redirect("autenticacion:roles")


@never_cache
@permiso_requerido("PERMISO_VER")
def permisos(request):
    permisos_lista = Permiso.objects.order_by("modulo", "codigo")
    return render(request, "autenticacion/permisos.html", {
        "usuario": request.usuario_actual,
        "permisos": permisos_lista,
    })


@never_cache
@permiso_requerido("SESION_VER")
def sesiones(request):
    estado = request.GET.get("estado", "activas")
    listado = Sesion.objects.select_related("usuario")
    if estado == "activas":
        listado = listado.filter(fecha_cierre__isnull=True, fecha_expiracion__gt=timezone.now())
    elif estado == "revocadas":
        listado = listado.filter(fecha_cierre__isnull=False)
    elif estado == "expiradas":
        listado = listado.filter(fecha_cierre__isnull=True, fecha_expiracion__lte=timezone.now())
    pagina = Paginator(listado.order_by("-fecha_inicio"), 20).get_page(request.GET.get("pagina"))
    return render(request, "autenticacion/sesiones.html", {
        "usuario": request.usuario_actual,
        "sesiones": pagina,
        "estado": estado,
        "now": timezone.now(),
    })


@never_cache
@require_POST
@permiso_requerido("SESION_REVOCAR")
def sesion_revocar(request, sesion_id):
    try:
        revocar_sesion_seguridad(sesion_id, request.usuario_actual, _direccion_ip(request))
        messages.success(request, "La sesión fue revocada.")
    except Sesion.DoesNotExist:
        raise Http404("La sesión no existe.")
    return redirect("autenticacion:sesiones")


@never_cache
@permiso_requerido("ACCESO_VER")
def accesos(request):
    listado = Acceso.objects.select_related("usuario")
    resultado = request.GET.get("resultado", "")
    if resultado == "exitoso":
        listado = listado.filter(exitoso=True)
    elif resultado == "fallido":
        listado = listado.filter(exitoso=False)
    pagina = Paginator(listado.order_by("-fecha", "-id"), 30).get_page(request.GET.get("pagina"))
    return render(request, "autenticacion/accesos.html", {
        "usuario": request.usuario_actual,
        "accesos": pagina,
        "resultado": resultado,
    })


@never_cache
@permiso_requerido("AUDITORIA_VER")
def auditoria(request):
    listado = Auditoria.objects.order_by("-fecha", "-id")
    tabla = request.GET.get("tabla", "").strip()
    operacion = request.GET.get("operacion", "").strip().upper()
    if tabla:
        listado = listado.filter(tabla__icontains=tabla)
    if operacion in {"INSERT", "UPDATE", "DELETE"}:
        listado = listado.filter(operacion=operacion)
    pagina = Paginator(listado, 30).get_page(request.GET.get("pagina"))
    return render(request, "autenticacion/auditoria.html", {
        "usuario": request.usuario_actual,
        "eventos": pagina,
        "tabla_filtro": tabla,
        "operacion_filtro": operacion,
    })
