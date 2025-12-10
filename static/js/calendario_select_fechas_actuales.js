// static/js/calendario_select_fechas_actuales.js

document.addEventListener("DOMContentLoaded", function () {
    const fechaInicio = document.getElementById("id_eve_fecha_inicio");
    const fechaFin = document.getElementById("id_eve_fecha_fin");

    // 🔒 Desactivar campo de fin al inicio
    fechaFin.disabled = true;

    // Obtener la fecha actual en formato YYYY-MM-DD
    const hoy = new Date().toISOString().split("T")[0];
    fechaInicio.min = hoy;

    // Cuando cambia la fecha de inicio
    fechaInicio.addEventListener("change", function () {
        if (fechaInicio.value) {
            fechaFin.disabled = false;
            fechaFin.min = fechaInicio.value; // La fecha fin mínima es la fecha inicio
        } else {
            fechaFin.disabled = true;
            fechaFin.value = "";
        }
    });

    // Cuando cambia la fecha de fin, validar en frontend
    fechaFin.addEventListener("change", function () {
        if (fechaFin.value < fechaInicio.value) {
            alert("⚠️ La fecha de finalización no puede ser anterior a la fecha de inicio.");
            fechaFin.value = "";
        }
    });
});
