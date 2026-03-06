'use strict';
(function () {
    // Селектор головного поля інтервалу оливи
    const SOURCE_SELECTOR = '#id_oil_change_interval_km';
    // Суфікс полів інтервалу у рядках inline
    const TARGET_SUFFIX   = '-change_interval_km';

    function getSourceValue() {
        const src = document.querySelector(SOURCE_SELECTOR);
        return src ? src.value.trim() : '';
    }

    // Заповнює порожні поля change_interval_km значенням з oil_change_interval_km
    function autofillEmptyTargets(sourceValue) {
        if (!sourceValue) return;
        document.querySelectorAll(`input[id$="${TARGET_SUFFIX}"]`).forEach(function (input) {
            if (input.value.trim() === '') {
                input.value = sourceValue;
            }
        });
    }

    // Заповнює конкретний новий рядок при додаванні
    function autofillNewRow(row) {
        const sourceValue = getSourceValue();
        if (!sourceValue) return;
        row.querySelectorAll(`input[id$="${TARGET_SUFFIX}"]`).forEach(function (input) {
            if (input.value.trim() === '') {
                input.value = sourceValue;
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        const source = document.querySelector(SOURCE_SELECTOR);
        if (!source) return;

        // Підписуємось на зміну головного поля (change — після завершення вводу)
        source.addEventListener('change', function () {
            autofillEmptyTargets(source.value.trim());
        });

        // При завантаженні сторінки — заповнюємо вже наявні порожні рядки
        autofillEmptyTargets(getSourceValue());

        // Обробляємо нові рядки, що додаються через кнопку "Додати ще"
        document.addEventListener('formset:added', function (event) {
            autofillNewRow(event.target);
        });
    });
}());
