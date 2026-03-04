$(document).ready(function() {
    // Инициализация наблюдателя за изменением списка
    const addressLocationSelect = $('ul[data-role="address-location-select"]');
    if (addressLocationSelect.length) {
        const observer = new MutationObserver((mutationsList) => {
            mutationsList.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    const selectedItem = addressLocationSelect.find('li.selected');
                    const locationSlug = selectedItem.data('value');
                    if (locationSlug) {
                        window.location = `${window.location.pathname}?location=${locationSlug}`;
                    }
                }
            });
        });

        observer.observe(addressLocationSelect[0], {
            childList: true,
            subtree: true
        });
    }

    // Инициализация Яндекс.Карт
    ymaps.ready(init);
});

const YAMAP_CONTAINER_ID = 'yamap_addresses';

function init() {
    const yamapContainer = $(`#${YAMAP_CONTAINER_ID}`);
    if (!yamapContainer.length) {
        console.error(`Контейнер с id="${YAMAP_CONTAINER_ID}" не найден.`);
        return;
    }

    // Проверка данных контейнера
    const centerLat = parseFloat(yamapContainer.data('center-latitude'));
    const centerLng = parseFloat(yamapContainer.data('center-longitude'));
    const zoomLevel = parseInt(yamapContainer.data('center-zoom'), 10);

    if (isNaN(centerLat) || isNaN(centerLng)) {
        console.error('Некорректные координаты центра карты.');
        return;
    }

    if (isNaN(zoomLevel)) {
        console.error('Некорректный уровень масштабирования.');
        return;
    }

    // Создание карты
    const myMap = new ymaps.Map(YAMAP_CONTAINER_ID, {
        center: [centerLat, centerLng],
        zoom: zoomLevel
    }, {
        searchControlProvider: 'yandex#search'
    });

    // Добавление точек на карту
    add_points(myMap, '.address-data');

    // Маркер главного магазина (адрес + своя иконка в круге)
    const mainStoreLat = yamapContainer.data('main-store-lat');
    const mainStoreLng = yamapContainer.data('main-store-lng');
    const mainStoreIcon = yamapContainer.data('main-store-icon');
    if (mainStoreLat != null && mainStoreLng != null && mainStoreIcon) {
        const lat = parseFloat(mainStoreLat);
        const lng = parseFloat(mainStoreLng);
        if (!isNaN(lat) && !isNaN(lng)) {
            const iconUrl = mainStoreIcon.indexOf('/') === 0 ? (window.location.origin + mainStoreIcon) : mainStoreIcon;
            const size = 48;
            const half = size / 2;
            const placemark = new ymaps.Placemark([lat, lng], {
                hintContent: 'Г. Самара, ул. Ново-Садовая, д. 179',
                balloonContent: 'Г. Самара, ул. Ново-Садовая, д. 179'
            }, {
                iconLayout: 'default#image',
                iconImageHref: iconUrl,
                iconImageSize: [size, size],
                iconImageOffset: [-half, -half],
                iconShape: {
                    type: 'Circle',
                    coordinates: [0, 0],
                    radius: half
                }
            });
            myMap.geoObjects.add(placemark);
        }
    }
}

function add_points(map, elementSelector) {
    $(elementSelector).each(function() {
        const $this = $(this);

        // Проверка данных для точки
        const latitude = parseFloat($this.data('latitude'));
        const longitude = parseFloat($this.data('longitude'));

        if (isNaN(latitude) || isNaN(longitude)) {
            console.error('Некорректные координаты точки:', $this);
            return;
        }

        const balloonContent = $this.data('balloon-content') || '';
        const hintContent = $this.data('hint-content') || '';
        const iconPreset = $this.data('icon-preset') || 'default';
        const glyphIconName = $this.data('glyph-icon-name') || '';
        const glyphIconColor = $this.data('glyph-icon-color') || '#000';

        // Создание геообъекта
        const myGeoObject = new ymaps.GeoObject({
            geometry: {
                type: "Point",
                coordinates: [latitude, longitude]
            },
            properties: {
                balloonContent,
                hintContent
            }
        }, {
            preset: `islands#${iconPreset}`,
            iconGlyph: glyphIconName,
            iconGlyphColor: glyphIconColor,
            draggable: false
        });

        // Добавление точки на карту
        map.geoObjects.add(myGeoObject);
    });
}
