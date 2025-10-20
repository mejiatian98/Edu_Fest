// static/js/marcar_campos_vacios_par.js

document.addEventListener("DOMContentLoaded", function () {
    // Seleccionamos todos los inputs, selects y textareas del formulario del participante
    const campos = document.querySelectorAll("form input, form select, form textarea");

    campos.forEach(campo => {
        const idCampo = campo.getAttribute("id");

        // No aplicar a campos ocultos ni a botones
        if (!idCampo || campo.type === "hidden" || campo.type === "submit") return;

        // ✅ Marcar todos como requeridos (ya los tienes en el form, pero reforzamos)
        campo.setAttribute("required", "required");

        // Buscar el label asociado al campo
        const label = campo.closest(".mb-3, .col-md-4, .col-md-6, .col-md-12")?.querySelector("label");
        if (!label) return;

        // Crear el asterisco (*)
        let asterisco = document.createElement("span");
        asterisco.textContent = " *";
        asterisco.style.color = "red";
        asterisco.style.display = "none"; // Oculto al inicio
        asterisco.classList.add("campo-obligatorio");
        label.appendChild(asterisco);

        // 🔁 Función para mostrar/ocultar el asterisco
        function actualizarAsterisco() {
            const valor = campo.value.trim();
            if (!valor) {
                asterisco.style.display = "inline";
                campo.style.borderColor = "red";
            } else {
                asterisco.style.display = "none";
                campo.style.borderColor = "";
            }
        }

        // Detectar cambios
        campo.addEventListener("input", actualizarAsterisco);
        campo.addEventListener("change", actualizarAsterisco);

        // Revisar al cargar
        actualizarAsterisco();
    });

    // 🚨 Validación general al enviar el formulario
    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", function (e) {
            let hayErrores = false;

            campos.forEach(campo => {
                const idCampo = campo.getAttribute("id");

                if (!idCampo || campo.type === "hidden" || campo.type === "submit") return;

                if (campo.value.trim() === "") {
                    campo.style.borderColor = "red";
                    hayErrores = true;
                }
            });

            if (hayErrores) {
                e.preventDefault();
                alert("⚠️ Por favor, completa todos los campos obligatorios antes de continuar.");
            }
        });
    }
});
