from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.template.loader import get_template
from django.test import RequestFactory, SimpleTestCase

from .decorators import permiso_requerido


class SesionFalsa(dict):
    def flush(self):
        self.clear()


class ControlAccesoTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.usuario = SimpleNamespace(id=7, activo=True, eliminado=False, esta_bloqueado=False)
        self.sesion_id = uuid4()

    def _preparar_mocks(self, permission=True, session=True):
        user_qs = MagicMock()
        user_qs.first.return_value = self.usuario
        session_qs = MagicMock()
        session_qs.exists.return_value = session
        permission_qs = MagicMock()
        permission_qs.exists.return_value = permission
        return (
            patch("apps.autenticacion.decorators.Usuario.objects.filter", return_value=user_qs),
            patch("apps.autenticacion.decorators.Sesion.objects.filter", return_value=session_qs),
            patch("apps.autenticacion.decorators.RolPermiso.objects.filter", return_value=permission_qs),
        )

    def test_protected_view_redirects_without_login(self):
        view = permiso_requerido("DASHBOARD_VER")(lambda request: HttpResponse("ok"))
        request = self.factory.get("/")
        request.session = SesionFalsa()
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_revoked_or_missing_session_is_rejected(self):
        view = permiso_requerido("DASHBOARD_VER")(lambda request: HttpResponse("ok"))
        request = self.factory.get("/")
        request.session = SesionFalsa(usuario_id=7, seguridad_sesion_id=str(self.sesion_id))
        user_patch, session_patch, _ = self._preparar_mocks(session=False)
        with user_patch, session_patch:
            response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("usuario_id", request.session)

    def test_user_without_module_permission_is_denied(self):
        view = permiso_requerido("USUARIO_ELIMINAR")(lambda request: HttpResponse("ok"))
        request = self.factory.get("/")
        request.session = SesionFalsa(usuario_id=7, seguridad_sesion_id=str(self.sesion_id))
        user_patch, session_patch, permission_patch = self._preparar_mocks(permission=False)
        with user_patch, session_patch, permission_patch:
            with self.assertRaises(PermissionDenied):
                view(request)

    def test_authorized_user_with_active_session_can_continue(self):
        view = permiso_requerido("DASHBOARD_VER")(lambda request: HttpResponse("ok"))
        request = self.factory.get("/")
        request.session = SesionFalsa(usuario_id=7, seguridad_sesion_id=str(self.sesion_id))
        user_patch, session_patch, permission_patch = self._preparar_mocks()
        with user_patch, session_patch, permission_patch:
            response = view(request)
        self.assertEqual(response.status_code, 200)

    def test_security_templates_compile(self):
        for template in (
            "autenticacion/roles.html",
            "autenticacion/rol_form.html",
            "autenticacion/rol_permisos.html",
            "autenticacion/permisos.html",
            "autenticacion/sesiones.html",
            "autenticacion/accesos.html",
            "autenticacion/auditoria.html",
            "autenticacion/usuario_password.html",
            "autenticacion/usuario_roles.html",
        ):
            with self.subTest(template=template):
                request = self.factory.get("/")
                request.resolver_match = SimpleNamespace(url_name="roles")
                get_template(template).render({
                    "request": request,
                    "usuario": self.usuario,
                })
