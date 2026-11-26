from django import forms
from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from PIL import Image, UnidentifiedImageError

from apps.autenticacion.models import Rol
from . import models
from .selectors import RECURSOS


FORM_FIELDS = {
    "empresa": ("ruc", "razon_social", "nombre_comercial", "direccion", "ubigeo", "telefono", "correo", "sitio_web", "representante_legal", "moneda"),
    "sucursales": ("codigo", "nombre", "direccion", "ubigeo", "empresa"),
    "monedas": ("codigo", "nombre", "simbolo"),
    "tipos-cambio": ("moneda_origen", "moneda_destino", "fecha", "tasa_compra", "tasa_venta", "fuente"),
    "tipos-documento": ("codigo", "nombre"),
    "medios-pago": ("nombre", "requiere_referencia"),
    "tipos-garantia": ("codigo", "nombre", "naturaleza"),
    "feriados": ("fecha", "descripcion"),
    "frecuencias-pago": ("codigo", "nombre", "descripcion", "unidad", "intervalo"),
    "productos": ("codigo", "nombre", "descripcion", "moneda", "monto_minimo", "monto_maximo", "plazo_minimo", "plazo_maximo", "porcentaje_financiamiento"),
    "limites-interes": ("moneda", "regimen", "tasa_compensatoria_maxima", "tasa_moratoria_maxima", "vigente_desde", "vigente_hasta", "fuente_oficial"),
    "tasas-interes": ("producto", "limite_interes", "tea", "tasa_moratoria", "vigente_desde", "vigente_hasta"),
    "politicas-crediticias": ("producto", "condiciones", "vigente_desde", "vigente_hasta"),
    "niveles-aprobacion": ("rol", "moneda", "monto_desde", "monto_hasta"),
    "conceptos-cobro": ("codigo", "nombre", "fundamento"),
    "correlativos": ("sucursal", "tipo_documento", "serie", "prefijo", "longitud"),
    "parametros": ("codigo", "nombre", "descripcion", "categoria", "valor", "tipo_dato"),
}


class LogoEmpresaField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("label", "Logo institucional")
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        archivo = super().clean(data, initial)
        if not archivo:
            return archivo
        if archivo.size > 2 * 1024 * 1024:
            raise ValidationError("El logo no puede superar 2 MB.")
        try:
            imagen = Image.open(archivo)
            if imagen.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValidationError("El logo debe ser PNG, JPG o WEBP.")
            if imagen.width > 4000 or imagen.height > 4000:
                raise ValidationError("Las dimensiones máximas del logo son 4000 × 4000 píxeles.")
            imagen.verify()
            archivo.seek(0)
        except (UnidentifiedImageError, OSError) as exc:
            raise ValidationError("El archivo no es una imagen válida.") from exc
        return archivo


class ConfiguracionBaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                field.widget.attrs.setdefault("class", "config-checkbox")
            else:
                field.widget.attrs.setdefault("class", "config-control")
        if "rol" in self.fields:
            self.fields["rol"].queryset = Rol.objects.filter(activo=True).order_by("nombre")
        for name in ("moneda", "moneda_origen", "moneda_destino"):
            if name in self.fields:
                self.fields[name].queryset = models.Moneda.objects.filter(activo=True).order_by("codigo")
        if "ubigeo" in self.fields:
            self.fields["ubigeo"].queryset = models.Ubigeo.objects.order_by("departamento", "provincia", "distrito")
        if "empresa" in self.fields:
            self.fields["empresa"].queryset = models.Empresa.objects.filter(activo=True).order_by("razon_social")
        if "frecuencia_pago" in self.fields:
            self.fields["frecuencia_pago"].queryset = models.FrecuenciaPago.objects.filter(activo=True).order_by("nombre")
        if "tipo_garantia" in self.fields:
            self.fields["tipo_garantia"].queryset = models.TipoGarantia.objects.filter(activo=True).order_by("nombre")
        if "producto" in self.fields:
            self.fields["producto"].queryset = models.ProductoCrediticio.objects.filter(activo=True).order_by("nombre")
        if "limite_interes" in self.fields:
            self.fields["limite_interes"].queryset = models.LimiteInteres.objects.order_by("-vigente_desde")
        if "naturaleza" in self.fields:
            self.fields["naturaleza"].choices = (("MOBILIARIA", "Mobiliaria"), ("HIPOTECARIA", "Hipotecaria"))
        if "unidad" in self.fields:
            self.fields["unidad"].choices = (("DIA", "Día"), ("SEMANA", "Semana"), ("MES", "Mes"))
        if "tipo_dato" in self.fields:
            self.fields["tipo_dato"].choices = (("TEXTO", "Texto"), ("NUMERO", "Número"), ("BOOLEANO", "Booleano"), ("JSON", "JSON"))
        for name in ("fecha", "vigente_desde", "vigente_hasta"):
            if name in self.fields:
                self.fields[name].widget = forms.DateInput(attrs={"type": "date", "class": "config-control"})


def formulario_recurso(slug, *args, **kwargs):
    model = RECURSOS[slug]["modelo"]
    fields = FORM_FIELDS[slug]
    if slug == "politicas-crediticias":
        form_class = type("PoliticaCrediticiaForm", (ConfiguracionBaseForm,), {
            "condiciones": forms.JSONField(
                label="Condiciones (JSON)",
                widget=forms.Textarea(attrs={"rows": 8, "placeholder": '{"criterio": "valor"}'}),
                help_text="Define aquí las condiciones aprobadas por la empresa. No incluyas datos personales.",
            ),
        })
    elif slug == "parametros":
        form_class = type("ParametroSistemaForm", (ConfiguracionBaseForm,), {
            "valor": forms.JSONField(label="Valor (JSON)", widget=forms.Textarea(attrs={"rows": 4})),
        })
    else:
        form_class = ConfiguracionBaseForm
    Meta = type("Meta", (), {"model": model, "fields": fields})
    form_class.Meta = Meta
    if slug == "empresa":
        form_class.base_fields["logo_archivo"] = LogoEmpresaField()
        form_class.base_fields["logo_archivo"].widget.attrs["class"] = "config-control"
    generated = modelform_factory(model, form=type(f"{model.__name__}Form", (form_class,), {}), fields=fields)
    if slug == "empresa":
        generated.base_fields["logo_archivo"] = LogoEmpresaField()
        generated.base_fields["logo_archivo"].widget.attrs["class"] = "config-control"
    if slug in {"politicas-crediticias", "parametros"}:
        generated.base_fields["condiciones" if slug == "politicas-crediticias" else "valor"] = form_class.base_fields["condiciones" if slug == "politicas-crediticias" else "valor"]
    return generated(*args, **kwargs)


class ProductoRelacionesForm(forms.Form):
    garantias = forms.ModelMultipleChoiceField(
        label="Garantías permitidas", required=False,
        queryset=models.TipoGarantia.objects.filter(activo=True).order_by("naturaleza", "nombre"),
        widget=forms.CheckboxSelectMultiple,
    )
    frecuencias = forms.ModelMultipleChoiceField(
        label="Frecuencias permitidas", required=False,
        queryset=models.FrecuenciaPago.objects.filter(activo=True).order_by("nombre"),
        widget=forms.CheckboxSelectMultiple,
    )


class UbigeoImportForm(forms.Form):
    archivo = forms.FileField(label="Archivo CSV oficial", help_text="UTF-8, máximo 5 MB. Columnas: codigo, departamento, provincia, distrito.")


class AuditoriaFiltroForm(forms.Form):
    usuario = forms.CharField(required=False, label="Usuario")
    tabla = forms.CharField(required=False, label="Tabla")
    operacion = forms.ChoiceField(required=False, choices=(("", "Todas"), ("INSERT", "Creación"), ("UPDATE", "Modificación"), ("DELETE", "Eliminación"), ("IMPORT", "Importación")))
    desde = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    hasta = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
