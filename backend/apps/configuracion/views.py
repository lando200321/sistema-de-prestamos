import csv
from datetime import date

from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods

from apps.autenticacion.decorators import sesion_requerida
from apps.autenticacion.models import Auditoria
from . import models
from .forms import ProductoRelacionesForm, UbigeoImportForm, formulario_recurso
from .selectors import GRUPOS, RECURSOS, filas_para_tabla, listar_recurso, permisos_usuario, resumen_panel
from .services import ConfiguracionService, ProductoRelacionesService, UbigeoImportService


def _exigir(request, permiso):
    if permiso not in permisos_usuario(request.usuario_actual):
        raise PermissionDenied("No tienes permiso para realizar esta acción.")


@never_cache
@sesion_requerida
def panel(request):
    _exigir(request, "CONFIGURACION_VER")
    return render(request, "configuracion/panel.html", {
        "usuario": request.usuario_actual,
        "resumen": resumen_panel(request.usuario_actual),
        "grupos": GRUPOS,
    })


@never_cache
@sesion_requerida
def listado(request, slug):
    recurso = RECURSOS.get(slug)
    if recurso is None:
        raise Http404("El catálogo solicitado no existe.")
    _exigir(request, recurso["permiso_ver"])
    termino = request.GET.get("buscar", "").strip()[:100]
    estado = request.GET.get("estado", "")
    anio = request.GET.get("anio", "")
    fecha = request.GET.get("fecha", "")[:10]
    if fecha:
        try:
            date.fromisoformat(fecha)
        except ValueError:
            messages.error(request, "La fecha de filtro no es válida.")
            fecha = ""
    moneda = request.GET.get("moneda", "")[:3]
    fuente = request.GET.get("fuente", "")[:100]
    listado = listar_recurso(recurso, termino, estado, anio, fecha, moneda, fuente)
    pagina = Paginator(listado, 20).get_page(request.GET.get("pagina"))
    permisos = permisos_usuario(request.usuario_actual)
    filtros_url = request.GET.copy()
    filtros_url.pop("pagina", None)
    return render(request, "configuracion/listado.html", {
        "usuario": request.usuario_actual,
        "recurso": recurso,
        "slug": slug,
        "filas": filas_para_tabla(pagina.object_list, recurso["campos"]),
        "pagina": pagina,
        "buscar": termino,
        "estado": estado,
        "anio": anio,
        "fecha": fecha,
        "moneda": moneda,
        "fuente": fuente,
        "monedas": models.Moneda.objects.filter(activo=True).order_by("codigo") if slug in {"tipos-cambio", "productos", "tasas-interes"} else (),
        "puede_crear": recurso.get("permiso_crear") in permisos if recurso.get("permiso_crear") else False,
        "puede_editar": recurso.get("permiso_editar") in permisos if recurso.get("permiso_editar") else False,
        "puede_activar": f"{recurso.get('prefijo_permiso', '').upper()}_ACTIVAR" in permisos,
        "puede_desactivar": f"{recurso.get('prefijo_permiso', '').upper()}_DESACTIVAR" in permisos,
        "tiene_estado": any(field.name == "activo" for field in recurso["modelo"]._meta.fields),
        "usuario_permisos": permisos,
        "filtros_url": filtros_url.urlencode(),
        "puede_configurar_relaciones": {"PRODUCTO_ASIGNAR_GARANTIA", "PRODUCTO_ASIGNAR_FRECUENCIA"}.issubset(permisos),
    })


@never_cache
@sesion_requerida
@require_http_methods(["GET", "POST"])
def formulario(request, slug, pk=None):
    recurso = RECURSOS.get(slug)
    if recurso is None:
        raise Http404("El catálogo solicitado no existe.")
    es_edicion = pk is not None
    _exigir(request, recurso.get("permiso_editar") if es_edicion else recurso.get("permiso_crear"))
    if es_edicion and not recurso.get("permiso_editar"):
        raise Http404("Este registro se conserva por historial y no se edita.")
    modelo = recurso["modelo"]
    instancia = get_object_or_404(modelo, pk=pk) if es_edicion else modelo()

    if slug == "empresa" and modelo.objects.exists() and not es_edicion:
        messages.info(request, "Ya existe una empresa registrada. Edita sus datos institucionales.")
        return redirect(f"configuracion:{slug.replace('-', '_')}")
    if slug == "politicas-crediticias" and es_edicion:
        raise Http404("Las políticas son inmutables; registra una nueva versión.")
    if slug == "politicas-crediticias" and request.method == "POST":
        _exigir(request, "POLITICA_CREDITICIA_VERSIONAR")

    form = formulario_recurso(slug, request.POST or None, request.FILES or None, instance=instancia)
    if request.method == "POST" and form.is_valid():
        try:
            instancia = form.save(commit=False)
            logo = form.cleaned_data.get("logo_archivo") if slug == "empresa" else None
            ConfiguracionService.guardar(instancia, dict(form.cleaned_data), request.usuario_actual, logo)
            messages.success(request, f"{recurso['titulo']} guardado correctamente.")
            return redirect(f"configuracion:{slug.replace('-', '_')}")
        except ValidationError as error:
            form.add_error(None, error)
        except IntegrityError:
            form.add_error(None, "No se pudo guardar: verifica códigos duplicados y relaciones existentes.")
    return render(request, "configuracion/formulario.html", {
        "usuario": request.usuario_actual,
        "recurso": recurso,
        "slug": slug,
        "formulario": form,
        "es_edicion": es_edicion,
        "instancia": instancia,
        "media_url": settings.MEDIA_URL,
    })


@never_cache
@sesion_requerida
@require_POST
def cambiar_estado(request, slug, pk):
    recurso = RECURSOS.get(slug)
    if recurso is None:
        raise Http404("El catálogo solicitado no existe.")
    instancia = get_object_or_404(recurso["modelo"], pk=pk)
    if not hasattr(instancia, "activo"):
        raise Http404("Este registro no permite cambios de estado.")
    activo = not instancia.activo
    prefijo = slug.upper().replace("-", "_")
    _exigir(request, f"{prefijo}_{'ACTIVAR' if activo else 'DESACTIVAR'}")
    try:
        ConfiguracionService.cambiar_estado(instancia, activo, request.usuario_actual)
        messages.success(request, "Registro activado." if activo else "Registro desactivado.")
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    return redirect(f"configuracion:{slug.replace('-', '_')}")


@never_cache
@sesion_requerida
@require_http_methods(["GET", "POST"])
def relaciones_producto(request, producto_id):
    _exigir(request, "PRODUCTO_CREDITICIO_VER")
    producto = get_object_or_404(models.ProductoCrediticio, pk=producto_id)
    _exigir(request, "PRODUCTO_ASIGNAR_GARANTIA")
    _exigir(request, "PRODUCTO_ASIGNAR_FRECUENCIA")
    garantia_ids = models.ProductoGarantia.objects.filter(producto_id=producto.id).values_list("tipo_garantia_id", flat=True)
    frecuencia_ids = models.ProductoFrecuencia.objects.filter(producto_id=producto.id, activo=True).values_list("frecuencia_pago_id", flat=True)
    inicial_garantias = models.TipoGarantia.objects.filter(id__in=garantia_ids)
    inicial_frecuencias = models.FrecuenciaPago.objects.filter(id__in=frecuencia_ids)
    form = ProductoRelacionesForm(request.POST or None, initial={"garantias": inicial_garantias, "frecuencias": inicial_frecuencias})
    if request.method == "POST" and form.is_valid():
        try:
            ProductoRelacionesService.actualizar(producto.id, form.cleaned_data["garantias"], form.cleaned_data["frecuencias"], request.usuario_actual)
            messages.success(request, "Las garantías y frecuencias permitidas se actualizaron.")
            return redirect("configuracion:productos")
        except ValidationError as error:
            form.add_error(None, error)
    return render(request, "configuracion/relaciones_producto.html", {"usuario": request.usuario_actual, "producto": producto, "formulario": form})


@never_cache
@sesion_requerida
@require_http_methods(["GET", "POST"])
def importar_ubigeo(request):
    _exigir(request, "UBIGEO_IMPORTAR")
    form = UbigeoImportForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            total = UbigeoImportService.importar(form.cleaned_data["archivo"], request.usuario_actual, request.META.get("REMOTE_ADDR"))
            messages.success(request, f"Se importaron {total} códigos de ubigeo.")
            return redirect("configuracion:ubigeo")
        except ValidationError as error:
            form.add_error("archivo", error)
    return render(request, "configuracion/importar_ubigeo.html", {"usuario": request.usuario_actual, "formulario": form})


@never_cache
@sesion_requerida
def api_ubigeo(request):
    _exigir(request, "UBIGEO_VER")
    nivel = request.GET.get("nivel")
    consulta = models.Ubigeo.objects.all()
    if nivel == "departamentos":
        datos = list(consulta.values_list("departamento", flat=True).distinct().order_by("departamento"))
        return JsonResponse({"resultados": datos})
    departamento = request.GET.get("departamento", "")[:80]
    if nivel == "provincias" and departamento:
        datos = list(consulta.filter(departamento=departamento).values_list("provincia", flat=True).distinct().order_by("provincia"))
        return JsonResponse({"resultados": datos})
    provincia = request.GET.get("provincia", "")[:80]
    if nivel == "distritos" and departamento and provincia:
        datos = list(consulta.filter(departamento=departamento, provincia=provincia).values("codigo", "distrito").order_by("distrito"))
        return JsonResponse({"resultados": datos})
    codigo = request.GET.get("codigo", "")[:6]
    if nivel == "codigo" and codigo:
        ubicacion = consulta.filter(codigo=codigo).values("codigo", "departamento", "provincia", "distrito").first()
        return JsonResponse({"resultado": ubicacion})
    return JsonResponse({"resultados": []})


@never_cache
@sesion_requerida
def auditoria(request):
    _exigir(request, "CONFIGURACION_AUDITORIA_VER")
    consulta = Auditoria.objects.filter(esquema__in=("configuracion", "catalogo")).order_by("-fecha", "-id")
    usuario = request.GET.get("usuario", "").strip()[:80]
    tabla = request.GET.get("tabla", "").strip()[:100]
    operacion = request.GET.get("operacion", "").strip().upper()
    desde = request.GET.get("desde", "")
    hasta = request.GET.get("hasta", "")
    if usuario:
        filtro_usuario = Q(usuario_bd__icontains=usuario)
        if usuario.isdigit():
            filtro_usuario |= Q(usuario_aplicacion_id=int(usuario))
        consulta = consulta.filter(filtro_usuario)
    if tabla:
        consulta = consulta.filter(tabla__icontains=tabla)
    if operacion in {"INSERT", "UPDATE", "DELETE", "IMPORT"}:
        consulta = consulta.filter(operacion=operacion)
    try:
        if desde:
            consulta = consulta.filter(fecha__date__gte=date.fromisoformat(desde))
        if hasta:
            consulta = consulta.filter(fecha__date__lte=date.fromisoformat(hasta))
    except ValueError:
        messages.error(request, "El rango de fechas no es válido.")
    pagina = Paginator(consulta, 30).get_page(request.GET.get("pagina"))
    return render(request, "configuracion/auditoria.html", {"usuario": request.usuario_actual, "registros": pagina, "filtros": request.GET, "puede_exportar": "CONFIGURACION_EXPORTAR" in permisos_usuario(request.usuario_actual)})


@never_cache
@sesion_requerida
def exportar_auditoria(request):
    _exigir(request, "CONFIGURACION_EXPORTAR")
    _exigir(request, "CONFIGURACION_AUDITORIA_VER")
    consulta = Auditoria.objects.filter(esquema__in=("configuracion", "catalogo")).order_by("-fecha", "-id")[:10000]
    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = 'attachment; filename="auditoria_configuracion.csv"'
    respuesta.write("\ufeff")
    writer = csv.writer(respuesta)
    writer.writerow(("Fecha", "Usuario aplicación", "Usuario BD", "Esquema", "Tabla", "Operación", "IP"))
    for item in consulta.iterator():
        writer.writerow((item.fecha.isoformat(), item.usuario_aplicacion_id, item.usuario_bd, item.esquema, item.tabla, item.operacion, item.direccion_ip or ""))
    return respuesta


