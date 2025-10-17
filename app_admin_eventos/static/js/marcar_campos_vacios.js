// static/js/marcar_campos_vacios.js

document.addEventListener("DOMContentLoaded", function () {
    // Seleccionamos todos los campos del formulario
    const campos = document.querySelectorAll("form input, form select, form textarea");

    campos.forEach(campo => {
        // ❌ Excepciones: estos campos NO deben ser requeridos
        const idCampo = campo.getAttribute("id");
        if (idCampo === "cat_descripcion") {
            return; // se salta estos dos
        }

        // ✅ Aseguramos que todos los demás sean requeridos
        campo.setAttribute("required", "required");

        // Buscar la etiqueta label asociada al campo
        const label = campo.closest(".mb-3, .col-md-4, .col-md-6, .col-md-12")?.querySelector("label");
        if (!label) return;

        // Crear el asterisco (*)
        let asterisco = document.createElement("span");
        asterisco.textContent = " *";
        asterisco.style.color = "red";
        asterisco.style.display = "none"; // Oculto por defecto
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

        // Detecta cambios en tiempo real
        campo.addEventListener("input", actualizarAsterisco);
        campo.addEventListener("change", actualizarAsterisco);

        // Revisar al inicio
        actualizarAsterisco();
    });

    // 🚨 Validación al enviar: muestra los asteriscos en vacíos
    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", function (e) {
            let hayErrores = false;
            campos.forEach(campo => {
                const idCampo = campo.getAttribute("id");
                if (idCampo === "cat_descripcion") {
                    return;
                }
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
