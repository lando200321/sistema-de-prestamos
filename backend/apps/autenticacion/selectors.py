from django.db import connection
from django.db.models import Q
from django.utils import timezone
from .models import Usuario, Rol


MESES_CORTOS = (
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
)


class DashboardSelector:

    @staticmethod
    def obtener_indicadores():

        consulta = """
            SELECT
                (
                    SELECT COALESCE(SUM(capital), 0)
                    FROM operaciones.prestamo
                    WHERE fecha_desembolso IS NOT NULL
                    AND estado <> 'ANULADO'
                    AND moneda_codigo = 'PEN'
                ) AS capital_prestado,

                (
                    SELECT COUNT(*)
                    FROM operaciones.prestamo
                    WHERE estado IN (
                        'VIGENTE',
                        'VENCIDO',
                        'EN_COBRANZA',
                        'EN_EJECUCION'
                    )
                ) AS prestamos_activos,

                (
                    SELECT COUNT(*)
                    FROM cobranza.cuota AS c
                    INNER JOIN cobranza.cronograma AS cr
                        ON cr.id = c.cronograma_id
                    WHERE cr.vigente = TRUE
                    AND c.fecha_vencimiento < CURRENT_DATE
                    AND c.estado IN (
                        'PENDIENTE',
                        'PARCIAL',
                        'VENCIDA'
                    )
                ) AS cuotas_vencidas,

                (
                    SELECT COUNT(*)
                    FROM garantias.garantia
                    WHERE estado = 'VIGENTE'
                ) AS garantias_vigentes;
        """

        with connection.cursor() as cursor:
            cursor.execute(consulta)
            resultado = cursor.fetchone()

        return {
            "capital_prestado": resultado[0],
            "prestamos_activos": resultado[1],
            "cuotas_vencidas": resultado[2],
            "garantias_vigentes": resultado[3],
        }

    @staticmethod
    def obtener_resumen_operaciones():
        hoy = timezone.localdate()
        primer_mes = hoy.replace(day=1)
        meses = []
        year, month = primer_mes.year, primer_mes.month
        for _ in range(5):
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        year, month = year, month
        for _ in range(6):
            meses.append((year, month))
            month += 1
            if month == 13:
                month = 1
                year += 1

        inicio = date_for_month(*meses[0])
        fin = date_for_next_month(*meses[-1])
        prestamos_por_mes = {}
        recuperaciones_por_mes = {}

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT date_trunc('month', fecha_desembolso)::date AS mes,
                       COALESCE(SUM(capital), 0)
                FROM operaciones.prestamo
                WHERE fecha_desembolso >= %s
                  AND fecha_desembolso < %s
                  AND fecha_desembolso IS NOT NULL
                  AND estado <> 'ANULADO'
                  AND moneda_codigo = 'PEN'
                GROUP BY 1
                """,
                [inicio, fin],
            )
            prestamos_por_mes = {
                (row[0].year, row[0].month): float(row[1] or 0)
                for row in cursor.fetchall()
            }

            cursor.execute(
                """
                SELECT date_trunc('month', pago.fecha_pago)::date AS mes,
                       COALESCE(SUM(pago.monto), 0)
                FROM cobranza.pago AS pago
                INNER JOIN operaciones.prestamo AS prestamo
                    ON prestamo.id = pago.prestamo_id
                WHERE pago.fecha_pago >= %s
                  AND pago.fecha_pago < %s
                  AND pago.estado = 'CONFIRMADO'
                  AND prestamo.moneda_codigo = 'PEN'
                GROUP BY 1
                """,
                [inicio, fin],
            )
            recuperaciones_por_mes = {
                (row[0].year, row[0].month): float(row[1] or 0)
                for row in cursor.fetchall()
            }

            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(saldo_capital) FILTER (WHERE estado = 'VIGENTE'), 0),
                    COALESCE(SUM(saldo_capital) FILTER (WHERE estado NOT IN ('VIGENTE', 'CANCELADO', 'ANULADO')), 0)
                FROM operaciones.v_cartera_crediticia
                WHERE moneda_codigo = 'PEN'
                  AND estado NOT IN ('CANCELADO', 'ANULADO')
                """
            )
            cartera_row = cursor.fetchone()
            vigente = float(cartera_row[0] or 0)
            seguimiento = float(cartera_row[1] or 0)

            cursor.execute(
                """
                SELECT codigo_prestamo, nombre_cliente, capital,
                       fecha_desembolso, estado
                FROM operaciones.v_cartera_crediticia
                WHERE moneda_codigo = 'PEN'
                  AND fecha_desembolso IS NOT NULL
                  AND estado <> 'ANULADO'
                ORDER BY fecha_desembolso DESC, prestamo_id DESC
                LIMIT 5
                """
            )
            operaciones = cursor.fetchall()

        valores = [
            valor
            for clave in meses
            for valor in (prestamos_por_mes.get(clave, 0), recuperaciones_por_mes.get(clave, 0))
        ]
        mayor_valor = max(valores, default=0)
        escala = max(10000, int(((mayor_valor * 1.1 + 9999) // 10000) * 10000))

        serie_mensual = []
        for year, month in meses:
            prestado = prestamos_por_mes.get((year, month), 0)
            recuperado = recuperaciones_por_mes.get((year, month), 0)
            serie_mensual.append({
                "mes": MESES_CORTOS[month - 1],
                "prestado": prestado,
                "recuperado": recuperado,
                "prestado_pct": round(prestado / escala * 100, 2) if prestado else 0,
                "recuperado_pct": round(recuperado / escala * 100, 2) if recuperado else 0,
            })

        total_cartera = vigente + seguimiento
        porcentaje_vigente = round(vigente / total_cartera * 100) if total_cartera else 0
        eje_grafico = [
            {"valor": round(escala * fraccion), "posicion": posicion}
            for fraccion, posicion in ((1, 0), (.75, 25), (.5, 50), (.25, 75), (0, 100))
        ]
        operaciones_recientes = []
        etiquetas_estado = {
            "VIGENTE": ("Vigente", "vigente"),
            "PENDIENTE_DESEMBOLSO": ("Pendiente", "pendiente"),
            "VENCIDO": ("Vencido", "vencido"),
            "EN_COBRANZA": ("En cobranza", "vencido"),
            "EN_EJECUCION": ("En ejecución", "pendiente"),
            "REFINANCIADO": ("Refinanciado", "pendiente"),
            "CANCELADO": ("Cancelado", "cancelado"),
        }
        for codigo, cliente, monto, fecha, estado in operaciones:
            nombre_estado, clase_estado = etiquetas_estado.get(
                estado, (estado.replace("_", " ").title(), "pendiente")
            )
            operaciones_recientes.append({
                "codigo": codigo,
                "cliente": cliente,
                "monto": float(monto or 0),
                "fecha": fecha,
                "estado": nombre_estado,
                "clase_estado": clase_estado,
            })

        return {
            "serie_mensual": serie_mensual,
            "escala_grafico": escala,
            "eje_grafico": eje_grafico,
            "grafico_sin_datos": not any(valores),
            "cartera_vigente": vigente,
            "cartera_seguimiento": seguimiento,
            "cartera_total": total_cartera,
            "porcentaje_vigente": porcentaje_vigente,
            "porcentaje_seguimiento": 100 - porcentaje_vigente if total_cartera else 0,
            "cartera_sin_datos": total_cartera == 0,
            "operaciones_recientes": operaciones_recientes,
        }


def date_for_month(year, month):
    from datetime import date

    return date(year, month, 1)


def date_for_next_month(year, month):
    from datetime import date

    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)

# ==========================================
# CONSULTAS DE USUARIOS
# ==========================================

class UsuarioSelector:

    @staticmethod
    def obtener_indicadores():

        usuarios = Usuario.objects.filter(
            eliminado=False
        )

        return {
            "total": usuarios.count(),

            "activos": usuarios.filter(
                activo=True
            ).count(),

            "inactivos": usuarios.filter(
                activo=False
            ).count(),

            "bloqueados": usuarios.filter(
                bloqueado_hasta__gt=timezone.now()
            ).count(),
        }

    @staticmethod
    def listar_usuarios(busqueda="", estado="", rol=""):

        usuarios = Usuario.objects.filter(
            eliminado=False
        ).prefetch_related(
            "roles_asignados__rol"
        ).order_by("id")

        if busqueda:

            usuarios = usuarios.filter(
                Q(nombres__icontains=busqueda) |
                Q(apellidos__icontains=busqueda) |
                Q(nombre_usuario__icontains=busqueda) |
                Q(documento__icontains=busqueda) |
                Q(correo__icontains=busqueda)
            )

        if estado == "activo":

            usuarios = usuarios.filter(activo=True)

        elif estado == "inactivo":

            usuarios = usuarios.filter(activo=False)

        elif estado == "bloqueado":

            usuarios = usuarios.filter(
                bloqueado_hasta__gt=timezone.now()
            )

        if rol.isdigit():

            usuarios = usuarios.filter(
                roles_asignados__rol_id=rol
            )

        return usuarios.distinct()

    @staticmethod
    def listar_roles():

        return Rol.objects.filter(
            activo=True
        ).order_by("nombre")
