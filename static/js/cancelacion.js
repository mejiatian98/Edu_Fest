document.addEventListener("DOMContentLoaded", function () {
    const countdownEl = document.getElementById("countdown");

    if (countdownEl && countdownEl.dataset.cancelTime) {
        const cancelTimeStr = countdownEl.dataset.cancelTime;
        const cancelTime = new Date(cancelTimeStr).getTime();
        const expirationTime = cancelTime + 5 * 60 * 60 * 1000; // 5 horas

        function updateCountdown() {
            const now = new Date().getTime();
            const distance = expirationTime - now;

            if (distance <= 0) {
                countdownEl.innerHTML = "Tiempo expirado. El evento será eliminado pronto.";
                return;
            }

            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            countdownEl.innerHTML = `${hours}h ${minutes}m ${seconds}s`;
        }

        updateCountdown();
        setInterval(updateCountdown, 1000);
    }
});
