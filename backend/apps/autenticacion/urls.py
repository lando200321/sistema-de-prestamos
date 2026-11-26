from django.urls import path
from . import views

app_name = "autenticacion"

urlpatterns = [

    path("", views.iniciar_sesion, name="login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("logout/", views.cerrar_sesion, name="logout"),
    path("usuarios/nuevo/",views.usuario_crear,name="usuario_crear"),
    path("usuarios/<int:usuario_id>/editar/",views.usuario_editar,name="usuario_editar"),
    path("usuarios/<int:usuario_id>/activar/",views.usuario_activar,name="usuario_activar"),
    path("usuarios/<int:usuario_id>/desactivar/",views.usuario_desactivar,name="usuario_desactivar"),
    path("usuarios/<int:usuario_id>/eliminar/",views.usuario_eliminar,name="usuario_eliminar"),
    path("usuarios/<int:usuario_id>/desbloquear/", views.usuario_desbloquear, name="usuario_desbloquear"),
    path("usuarios/<int:usuario_id>/password/", views.usuario_restablecer_password, name="usuario_password"),
    path("usuarios/<int:usuario_id>/roles/", views.usuario_roles, name="usuario_roles"),
    path("roles/", views.roles, name="roles"),
    path("roles/nuevo/", views.rol_crear, name="rol_crear"),
    path("roles/<int:rol_id>/editar/", views.rol_editar, name="rol_editar"),
    path("roles/<int:rol_id>/permisos/", views.rol_permisos, name="rol_permisos"),
    path("roles/<int:rol_id>/activar/", views.rol_activar, name="rol_activar"),
    path("roles/<int:rol_id>/desactivar/", views.rol_desactivar, name="rol_desactivar"),
    path("roles/<int:rol_id>/eliminar/", views.rol_eliminar, name="rol_eliminar"),
    path("permisos/", views.permisos, name="permisos"),
    path("sesiones/", views.sesiones, name="sesiones"),
    path("sesiones/<uuid:sesion_id>/revocar/", views.sesion_revocar, name="sesion_revocar"),
    path("accesos/", views.accesos, name="accesos"),
    path("auditoria/", views.auditoria, name="auditoria"),
]
