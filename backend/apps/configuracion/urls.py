from django.urls import path
from . import views
from .selectors import RECURSOS

app_name = "configuracion"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("auditoria/", views.auditoria, name="auditoria"),
    path("auditoria/exportar/", views.exportar_auditoria, name="auditoria_exportar"),
    path("ubigeo/importar/", views.importar_ubigeo, name="ubigeo_importar"),
    path("api/ubigeo/", views.api_ubigeo, name="api_ubigeo"),
    path("productos/<int:producto_id>/relaciones/", views.relaciones_producto, name="producto_relaciones"),
]

for slug in RECURSOS:
    nombre = slug.replace("-", "_")
    recurso = RECURSOS[slug]
    urlpatterns.append(path(f"{slug}/", views.listado, {"slug": slug}, name=nombre))
    if recurso.get("permiso_crear"):
        urlpatterns.append(path(f"{slug}/nuevo/", views.formulario, {"slug": slug}, name=f"{nombre}_nuevo"))
    if recurso.get("permiso_editar"):
        urlpatterns.append(path(f"{slug}/<str:pk>/editar/", views.formulario, {"slug": slug}, name=f"{nombre}_editar"))
    if any(field.name == "activo" for field in recurso["modelo"]._meta.fields):
        urlpatterns.append(path(f"{slug}/<str:pk>/estado/", views.cambiar_estado, {"slug": slug}, name=f"{nombre}_estado"))
