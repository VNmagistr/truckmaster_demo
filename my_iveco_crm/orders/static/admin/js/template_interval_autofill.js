'use strict';
(function () {
    const SOURCE_SELECTOR = '#id_engine_oil_interval';
    const TARGET_SUFFIX   = '-change_interval_km';

    function getSourceValue() {
        var src = document.querySelector(SOURCE_SELECTOR);
        return src ? src.value.trim() : '';
    }

    function autofillEmptyTargets(sourceValue) {
        if (!sourceValue) return;
        document.querySelectorAll('input[id$="' + TARGET_SUFFIX + '"]').forEach(function (input) {
            if (input.value.trim() === '') {
                input.value = sourceValue;
            }
        });
    }

    function autofillNewRow(row) {
        var sourceValue = getSourceValue();
        if (!sourceValue) return;
        row.querySelectorAll('input[id$="' + TARGET_SUFFIX + '"]').forEach(function (input) {
            if (input.value.trim() === '') {
                input.value = sourceValue;
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var source = document.querySelector(SOURCE_SELECTOR);
        if (!source) return;

        source.addEventListener('change', function () {
            autofillEmptyTargets(source.value.trim());
        });

        autofillEmptyTargets(getSourceValue());

        document.addEventListener('formset:added', function (event) {
            autofillNewRow(event.target);
        });
    });
}());
