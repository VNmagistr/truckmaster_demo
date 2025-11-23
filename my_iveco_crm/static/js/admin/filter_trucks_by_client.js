(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Знаходимо поля клієнта та вантажівки
        var clientField = $('#id_client');
        var truckField = $('#id_truck');
        
        // Якщо полів немає - виходимо
        if (!clientField.length || !truckField.length) {
            return;
        }
        
        // Зберігаємо початкове значення вантажівки (для редагування)
        var initialTruckValue = truckField.val();
        
        // Функція для оновлення списку вантажівок
        function updateTruckOptions(clientId, keepValue) {
            if (!clientId) {
                // Якщо клієнт не вибраний - очищаємо поле вантажівки
                clearTruckField();
                return;
            }
            
            // Отримуємо вантажівки для вибраного клієнта
            $.ajax({
                url: 'get-trucks-by-client/',
                data: { client_id: clientId },
                dataType: 'json',
                success: function(data) {
                    updateTruckSelect(data.trucks, keepValue);
                },
                error: function(xhr, status, error) {
                    console.error('Error fetching trucks:', error);
                }
            });
        }
        
        // Функція для оновлення select2 поля вантажівки
        function updateTruckSelect(trucks, keepValue) {
            // Для autocomplete поля (select2) потрібен інший підхід
            // Зберігаємо список дозволених ID
            window.allowedTruckIds = trucks.map(function(t) { return t.id; });
            
            // Якщо поточне значення не в списку - очищаємо
            var currentValue = truckField.val();
            if (currentValue && window.allowedTruckIds.length > 0) {
                if (window.allowedTruckIds.indexOf(parseInt(currentValue)) === -1 && !keepValue) {
                    clearTruckField();
                }
            }
            
            // Показуємо підказку якщо немає вантажівок
            if (trucks.length === 0) {
                showNoTrucksMessage();
            } else {
                hideNoTrucksMessage();
            }
        }
        
        // Очищення поля вантажівки
        function clearTruckField() {
            // Для select2
            if (truckField.hasClass('select2-hidden-accessible')) {
                truckField.val(null).trigger('change');
            } else {
                truckField.val('');
            }
        }
        
        // Показати повідомлення про відсутність вантажівок
        function showNoTrucksMessage() {
            var msg = $('#no-trucks-message');
            if (!msg.length) {
                truckField.closest('.related-widget-wrapper, .form-row, .field-truck')
                    .append('<p id="no-trucks-message" style="color: #999; font-style: italic; margin-top: 5px;">У цього клієнта немає зареєстрованих вантажівок</p>');
            }
        }
        
        // Приховати повідомлення
        function hideNoTrucksMessage() {
            $('#no-trucks-message').remove();
        }
        
        // Слухаємо зміни в полі клієнта
        // Для звичайного select
        clientField.on('change', function() {
            var clientId = $(this).val();
            updateTruckOptions(clientId, false);
        });
        
        // Для select2 (autocomplete)
        clientField.on('select2:select', function(e) {
            var clientId = e.params.data.id;
            updateTruckOptions(clientId, false);
        });
        
        clientField.on('select2:clear', function() {
            clearTruckField();
            hideNoTrucksMessage();
        });
        
        // Перевіряємо при завантаженні сторінки (для редагування існуючого замовлення)
        var initialClientId = clientField.val();
        if (initialClientId) {
            updateTruckOptions(initialClientId, true);
        }
        
        // Модифікуємо autocomplete для вантажівок щоб фільтрувати результати
        // Перехоплюємо AJAX запити select2 для поля truck
        $(document).on('select2:open', function() {
            // Додаємо фільтр до пошуку вантажівок
            var searchField = $('.select2-search__field');
            if (searchField.length) {
                searchField.attr('data-client-filter', clientField.val() || '');
            }
        });
    });
})(django.jQuery);
