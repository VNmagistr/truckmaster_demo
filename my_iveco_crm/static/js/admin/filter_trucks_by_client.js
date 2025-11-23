(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Чекаємо поки select2 ініціалізується
        setTimeout(initTruckFilter, 500);
    });
    
    function initTruckFilter() {
        var clientField = $('#id_client');
        var truckField = $('#id_truck');
        
        if (!clientField.length || !truckField.length) {
            return;
        }
        
        // Зберігаємо оригінальний URL для autocomplete вантажівок
        var truckSelect2 = truckField.data('select2');
        if (!truckSelect2) {
            // Якщо select2 ще не готовий - чекаємо
            setTimeout(initTruckFilter, 300);
            return;
        }
        
        // Очищення поля вантажівки при зміні клієнта
        function clearTruckIfNeeded(newClientId) {
            var currentTruckId = truckField.val();
            
            if (!currentTruckId || !newClientId) {
                truckField.val(null).trigger('change.select2');
                return;
            }
            
            // Перевіряємо чи поточна вантажівка належить новому клієнту
            $.ajax({
                url: '/admin/orders/serviceorder/get-trucks-by-client/',
                data: { client_id: newClientId },
                dataType: 'json',
                success: function(data) {
                    var truckIds = data.trucks.map(function(t) { return String(t.id); });
                    if (truckIds.indexOf(String(currentTruckId)) === -1) {
                        // Вантажівка не належить цьому клієнту - очищаємо
                        truckField.val(null).trigger('change.select2');
                    }
                }
            });
        }
        
        // Слухаємо зміни клієнта
        clientField.on('change', function() {
            clearTruckIfNeeded($(this).val());
        });
        
        // Для select2
        clientField.on('select2:select', function(e) {
            clearTruckIfNeeded(e.params.data.id);
        });
        
        clientField.on('select2:clear', function() {
            truckField.val(null).trigger('change.select2');
        });
        
        // Перехоплюємо AJAX запити до autocomplete вантажівок
        $(document).ajaxSend(function(event, jqXHR, settings) {
            // Перевіряємо чи це запит до autocomplete вантажівок
            if (settings.url && settings.url.indexOf('autocomplete') !== -1 && 
                settings.url.indexOf('truck') !== -1) {
                
                var clientId = clientField.val();
                if (clientId) {
                    // Додаємо client_id до URL
                    var separator = settings.url.indexOf('?') !== -1 ? '&' : '?';
                    settings.url += separator + 'client_id=' + clientId;
                }
            }
        });
    }
})(django.jQuery);
