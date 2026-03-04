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

var YAMAP_CONTAINER_ID = 'yamap_addresses';

function init() {
    var yamapContainer = $('#' + YAMAP_CONTAINER_ID);
    if (!yamapContainer.length) {
        return;
    }
    var centerLat = parseFloat(yamapContainer.data('center-latitude'));
    var centerLng = parseFloat(yamapContainer.data('center-longitude'));
    var zoomLevel = parseInt(yamapContainer.data('center-zoom'), 10);
    if (isNaN(centerLat) || isNaN(centerLng) || isNaN(zoomLevel)) {
        return;
    }

    myMap = new ymaps.Map(YAMAP_CONTAINER_ID, {
        center: [centerLat, centerLng],
        zoom: zoomLevel
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
        var lat = parseFloat($this.data('latitude'));
        var lng = parseFloat($this.data('longitude'));
        if (isNaN(lat) || isNaN(lng)) {
            return;
        }
        var myGeoObject = new ymaps.GeoObject({
            geometry: {
                type: "Point",
                coordinates: [lat, lng]
            },
            properties: {
                balloonContent: $this.data('balloon-content'),
                hintContent: $this.data('hint-content')
            }
        }, {
            preset: 'islands#' + ($this.data('icon-preset') || 'blueDotIcon'),
            iconGlyph: $this.data('glyph-icon-name'),
            iconGlyphColor: $this.data('glyph-icon-color') || '#000',
            draggable: false
        });
        map.geoObjects.add(myGeoObject);
    });
}
