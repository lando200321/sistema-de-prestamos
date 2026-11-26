from django.template.loader import get_template
from django.test import SimpleTestCase
from django.core.exceptions import ValidationError
from django.urls import reverse

from . import models
from .forms import FORM_FIELDS, formulario_recurso
from .selectors import RECURSOS, listar_recurso
from .services import CorrelativoService, ParametroSistemaService


class ConfiguracionStructureTests(SimpleTestCase):
    def test_representa_las_20_tablas_existentes_sin_gestionar_esquema(self):
        modelos = [
            models.Feriado, models.FrecuenciaPago, models.MedioPago,
            models.Moneda, models.TipoDocumento, models.TipoGarantia,
            models.Ubigeo, models.Empresa, models.Sucursal, models.TipoCambio,
            models.Correlativo, models.ParametroSistema, models.ConceptoCobro,
            models.LimiteInteres, models.ProductoCrediticio,
            models.ProductoGarantia, models.ProductoFrecuencia,
            models.TasaInteres, models.PoliticaCrediticia, models.NivelAprobacion,
        ]
        self.assertEqual(len(modelos), 20)
        self.assertTrue(all(model._meta.managed is False for model in modelos))
        self.assertEqual(set(RECURSOS) - {"ubigeo"}, set(FORM_FIELDS))

    def test_formularios_de_recursos_se_construyen(self):
        for slug in FORM_FIELDS:
            with self.subTest(recurso=slug):
                form = formulario_recurso(slug)
                self.assertTrue(form.fields)
                if slug == "empresa":
                    self.assertIn("logo_archivo", form.fields)

    def test_todas_las_plantillas_del_modulo_compilan(self):
        for plantilla in (
            "configuracion/panel.html", "configuracion/listado.html",
            "configuracion/formulario.html", "configuracion/relaciones_producto.html",
            "configuracion/importar_ubigeo.html", "configuracion/auditoria.html",
        ):
            with self.subTest(plantilla=plantilla):
                get_template(plantilla)

    def test_todos_los_recursos_tienen_rutas_de_listado_y_alta(self):
        for slug in RECURSOS:
            nombre = slug.replace("-", "_")
            with self.subTest(recurso=slug):
                self.assertTrue(reverse(f"configuracion:{nombre}"))
                if RECURSOS[slug].get("permiso_crear"):
                    self.assertTrue(reverse(f"configuracion:{nombre}_nuevo"))

    def test_consultas_de_listado_y_busqueda_se_compilan_para_todos_los_recursos(self):
        for slug, recurso in RECURSOS.items():
            with self.subTest(recurso=slug):
                consulta = listar_recurso(recurso, termino="prueba")
                consulta.query.sql_with_params()


class ConfiguracionValidationTests(SimpleTestCase):
    def test_parametro_valida_tipo_json(self):
        ParametroSistemaService.validar_valor("TEXTO", "PEN")
        ParametroSistemaService.validar_valor("NUMERO", 3)
        ParametroSistemaService.validar_valor("BOOLEANO", True)
        ParametroSistemaService.validar_valor("JSON", {"dias": 14})
        with self.assertRaises(ValidationError):
            ParametroSistemaService.validar_valor("BOOLEANO", "true")

    def test_correlativo_formatea_y_evitar_desbordamiento(self):
        serie = models.Correlativo(
            sucursal_id=1, tipo_documento="SOLICITUD", serie="A1",
            prefijo="SOL-", longitud=5, ultimo_numero=41,
        )
        self.assertEqual(CorrelativoService.formatear(serie, 42), "SOL-A100042")
        serie.longitud = 2
        with self.assertRaises(ValidationError):
            CorrelativoService.formatear(serie, 100)
