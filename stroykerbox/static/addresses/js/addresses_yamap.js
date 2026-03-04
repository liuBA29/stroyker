$(document).ready(function() {
    $('ul[data-role="address-location-select"]').on('DOMSubtreeModified', 'li.selected', function(event){
        var locationSlug = $(this).data('value');
        if (locationSlug) {
            window.location = window.location.pathname + '?location=' + locationSlug;
        }

    });

    var myMap;
    ymaps.ready(init);
});

const YAMAP_CONTAINER_ID = 'yamap_addresses';

function init () {
    // Создание экземпляра карты и его привязка к контейнеру с
    // заданным id ("map").
    const yamapContainer = $('#' + YAMAP_CONTAINER_ID);
    const centerCoords = [
        parseFloat(yamapContainer.data('center-latitude')),
        parseFloat(yamapContainer.data('center-longitude'))
    ];

    myMap = new ymaps.Map(YAMAP_CONTAINER_ID, {
        // При инициализации карты обязательно нужно указать
        // её центр и коэффициент масштабирования.
        center: centerCoords,
        zoom: parseInt(yamapContainer.data('center-zoom'))
    }, {
        searchControlProvider: 'yandex#search'
    });

    add_points(myMap, '.address-data');

    // Маркер главного магазина (адрес + своя иконка в круге)
    var mainStoreLat = yamapContainer.data('main-store-lat');
    var mainStoreLng = yamapContainer.data('main-store-lng');
    var mainStoreIcon = yamapContainer.data('main-store-icon');
    if (mainStoreLat != null && mainStoreLng != null && mainStoreIcon) {
        var lat = parseFloat(mainStoreLat);
        var lng = parseFloat(mainStoreLng);
        if (!isNaN(lat) && !isNaN(lng)) {
            var iconUrl = mainStoreIcon.indexOf('/') === 0 ? (window.location.origin + mainStoreIcon) : mainStoreIcon;
            var size = 48;
            var half = size / 2;
            var placemark = new ymaps.Placemark([lat, lng], {
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


function add_points(map, element) {
    $(element).each(function(index) {
        var $this = $(this);
        // Создаем геообъект с типом геометрии "Точка".
        var myGeoObject = new ymaps.GeoObject({
            // Описание геометрии.
            geometry: {
                type: "Point",
                coordinates:  [
                    parseFloat($this.data('latitude')),
                    parseFloat($this.data('longitude'))
                ]
            },
            // Свойства.
            properties: {
                // Контент метки.
                balloonContent: $this.data('balloon-content'),
                hintContent: $this.data('hint-content')
            }
        }, {
            // Опции.
            preset: 'islands#' + $this.data('icon-preset'),
            iconGlyph: $this.data('glyph-icon-name'),
            iconGlyphColor: $this.data('glyph-icon-color'),
            // Метку нельзя перемещать.
            draggable: false
        });

        map.geoObjects.add(myGeoObject);
    });

}
