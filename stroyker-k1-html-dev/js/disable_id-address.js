(function() {
    'use strict';
    
    // Функция для настройки textarea вместо input
    function configureAddressInput() {
        const addressInput = document.getElementById('id_address');
        
        if (addressInput && addressInput.tagName === 'INPUT') {
            // Заменяем input на textarea
            const textarea = document.createElement('textarea');
            textarea.id = addressInput.id;
            textarea.name = addressInput.name;
            textarea.value = addressInput.value || '';
            textarea.placeholder = "Укажите точку на карте";
            textarea.disabled = true;
            
            // Стили для textarea с прокруткой
            Object.assign(textarea.style, {
                width: '100%',
                minHeight: '40px',
                maxHeight: '120px', // ограничиваем максимальную высоту
                padding: '10px 12px',
                fontSize: '14px',
                lineHeight: '1.4',
                color: '#000',
                backgroundColor: '#f8f9fa',
                border: '1px solid #ced4da',
                borderRadius: '4px',
                cursor: 'default',
                resize: 'none',
                fontFamily: 'inherit',
                whiteSpace: 'pre-wrap',
                wordWrap: 'break-word',
                overflowWrap: 'break-word',
                boxSizing: 'border-box',
                overflowY: 'auto', // вертикальная прокрутка при необходимости
                overflowX: 'hidden' // горизонтальную скрываем
            });
            
            // Заменяем элемент
            addressInput.parentNode.replaceChild(textarea, addressInput);
            
            // Функция обновления адреса
            window.updateAddressFromMap = function(address) {
                textarea.value = address;
                console.log('Адрес установлен:', address);
            };
            
        } else if (addressInput) {
            // Если уже textarea или другой элемент
            addressInput.disabled = true;
            addressInput.placeholder = "Укажите точку на карте";
            
            Object.assign(addressInput.style, {
                width: '100%',
                minHeight: '40px',
                maxHeight: '120px',
                padding: '10px 12px',
                whiteSpace: 'pre-wrap',
                wordWrap: 'break-word',
                overflowWrap: 'break-word',
                overflowY: 'auto',
                overflowX: 'hidden'
            });
            
            window.updateAddressFromMap = function(address) {
                addressInput.value = address;
                console.log('Адрес установлен:', address);
            };
        }
    }
    
    // Запускаем функцию после загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', configureAddressInput);
    } else {
        configureAddressInput();
    }
    
})();