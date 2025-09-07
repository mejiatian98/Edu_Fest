function startCountdown(eventId, endDate) {
    const countdownElement = document.getElementById(`countdown-${eventId}`);
    const end = new Date(endDate);
    const updateCountdown = () => {
        const now = new Date().getTime();
        const distance = end - now;
        if (distance > 0) {
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            countdownElement.innerHTML = `Quedan ${days}d ${hours}h ${minutes}m ${seconds}s`;
            countdownElement.classList.add('countdown-text');
        } else {
            countdownElement.innerHTML = 'El tiempo ha terminado.';
        }
    };
    updateCountdown();
    setInterval(updateCountdown, 1000);
}

{% for evento in eventos %}
    {% if evento.eve_estado == 'Finalizado' %}
        startCountdown({{ evento.id }}, '{{ evento.deletion_date|date:"Y-m-d" }}');
    {% endif %}
{% endfor %}