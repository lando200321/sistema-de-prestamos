document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // CONFIRMAR CAMBIO DE ESTADO
    // ==========================================

    const formularios = document.querySelectorAll(
        ".formulario-estado"
    );

    formularios.forEach(function (formulario) {

        formulario.addEventListener("submit", function (evento) {

            const accion = formulario.dataset.accion;

            const usuario = formulario.dataset.usuario;

            let mensaje;

            if (accion === "desactivar") {

                mensaje =
                    "¿Estás seguro de desactivar al usuario " +
                    usuario +
                    "?\n\n" +
                    "El usuario no podrá acceder al sistema.";

            } else if (accion === "eliminar") {

                mensaje =
                    "Estas seguro de eliminar permanentemente la cuenta de " +
                    usuario +
                    "?\n\n" +
                    "La eliminacion puede rechazarse si existen operaciones o historial asociado.";

            } else if (accion === "desbloquear") {

                mensaje =
                    "¿Estás seguro de desbloquear la cuenta de " +
                    usuario +
                    "?";

            } else {

                mensaje =
                    "¿Estás seguro de activar al usuario " +
                    usuario +
                    "?";

            }

            if (!window.confirm(mensaje)) {

                evento.preventDefault();

            }

        });

    });


    // ==========================================
    // CERRAR NOTIFICACIONES
    // ==========================================

    const botonesCerrar = document.querySelectorAll(
        ".cerrar-notificacion"
    );

    botonesCerrar.forEach(function (boton) {

        boton.addEventListener("click", function () {

            const notificacion = boton.closest(
                ".notificacion"
            );

            if (notificacion) {

                notificacion.remove();

            }

        });

    });

});
