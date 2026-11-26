document.addEventListener("DOMContentLoaded", function () {

    const boton = document.getElementById("mostrar-password");
    const password = document.getElementById("id_password");

    if (boton && password) {

        boton.addEventListener("click", function () {

            const visible = password.type === "password";

            password.type = visible ? "text" : "password";

            boton.setAttribute("aria-pressed", String(visible));
            boton.setAttribute(
                "aria-label",
                visible ? "Ocultar contraseña" : "Mostrar contraseña"
            );

        });

    }

});
