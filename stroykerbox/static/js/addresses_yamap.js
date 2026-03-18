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

    function _isMobileMap() {
        return window.matchMedia && window.matchMedia('(max-width: 767px)').matches;
    }

    // Для настройки ракурса: на мобилке запоминаем центр/зум в localStorage,
    // чтобы после F5 карта не "откатывалась" и можно было подобрать идеальный вид.
    var _storageKey = 'yamap:' + YAMAP_CONTAINER_ID + ':mobile_view';
    function _loadSavedMobileView() {
        if (!_isMobileMap()) return null;
        try {
            var raw = window.localStorage.getItem(_storageKey);
            if (!raw) return null;
            var data = JSON.parse(raw);
            if (!data) return null;
            var lat = parseFloat(data.lat);
            var lng = parseFloat(data.lng);
            var z = parseInt(data.zoom, 10);
            if (isNaN(lat) || isNaN(lng) || isNaN(z)) return null;
            return { lat: lat, lng: lng, zoom: z };
        } catch (e) {
            return null;
        }
    }
    var _savedView = _loadSavedMobileView();
    if (_savedView) {
        centerLat = _savedView.lat;
        centerLng = _savedView.lng;
        zoomLevel = _savedView.zoom;
    } else if (_isMobileMap()) {
        // Дефолтный "красивый" ракурс для мобилки можно задать data-mobile-center-*
        var mLat = parseFloat(yamapContainer.data('mobile-center-latitude'));
        var mLng = parseFloat(yamapContainer.data('mobile-center-longitude'));
        var mZoom = parseInt(yamapContainer.data('mobile-center-zoom'), 10);
        if (!isNaN(mLat) && !isNaN(mLng) && !isNaN(mZoom)) {
            centerLat = mLat;
            centerLng = mLng;
            zoomLevel = mZoom;
        }
    }

    myMap = new ymaps.Map(YAMAP_CONTAINER_ID, {
        center: [centerLat, centerLng],
        zoom: zoomLevel
    }, {
        searchControlProvider: 'yandex#search'
    });

    add_points(myMap, '.address-data');

    // Сохраняем выбранный ракурс (только мобилка).
    if (_isMobileMap()) {
        myMap.events.add('actionend', function() {
            try {
                var c = myMap.getCenter();
                var z = myMap.getZoom();
                if (!c || typeof z === 'undefined') return;
                window.localStorage.setItem(_storageKey, JSON.stringify({
                    lat: c[0],
                    lng: c[1],
                    zoom: z
                }));
            } catch (e) {
                // ignore
            }
        });
    }

    function _focusMainStoreOnMobile(coords) {
        if (!_isMobileMap()) return;
        // Если пользователь уже зафиксировал свой ракурс (сохранён в localStorage),
        // не переопределяем центр/сдвигом маркера.
        if (_savedView) return;
        try {
            // Центрируем карту по маркеру и сдвигаем его вверх, чтобы он был виден над карточкой-оверлеем.
            myMap.setCenter(coords, zoomLevel, { duration: 0, checkZoomRange: true });
            setTimeout(function() {
                var overlay = document.querySelector('.index-8march-map-overlay');
                var mapEl = document.getElementById(YAMAP_CONTAINER_ID);
                if (!overlay || !mapEl) return;
                var overlayH = overlay.offsetHeight || 0;
                // Эмпирический сдвиг: половина высоты карточки + небольшой запас.
                var dy = Math.round(((overlayH || 360) / 2) + 72);
                // В ymaps положительный dy сдвигает карту вниз (маркер уходит вниз).
                // Чтобы маркер оказался ВЫШЕ карточки, двигаем карту ВВЕРХ (отрицательный dy).
                myMap.panBy([0, -dy], { duration: 0 });
            }, 80);
        } catch (e) {
            // no-op: карта должна остаться работоспособной даже без фокуса
        }
    }

    // Маркер главного магазина (адрес + своя иконка)
    var mainStoreLat = yamapContainer.data('main-store-lat');
    var mainStoreLng = yamapContainer.data('main-store-lng');
    var mainStoreIcon = yamapContainer.data('main-store-icon');
    if (mainStoreLat != null && mainStoreLng != null && mainStoreIcon) {
        var lat = parseFloat(mainStoreLat);
        var lng = parseFloat(mainStoreLng);
        if (!isNaN(lat) && !isNaN(lng)) {
            var iconUrl = mainStoreIcon.indexOf('/') === 0 ? (window.location.origin + mainStoreIcon) : mainStoreIcon;
            // Позволяем задавать размер иконки через data-атрибуты, чтобы избежать деформации PNG.
            var iconW = parseInt(yamapContainer.data('main-store-icon-w'), 10);
            var iconH = parseInt(yamapContainer.data('main-store-icon-h'), 10);
            if (isNaN(iconW) || iconW <= 0) iconW = 48;
            if (isNaN(iconH) || iconH <= 0) iconH = 48;
            var halfW = iconW / 2;
            var halfH = iconH / 2;
            var placemark = new ymaps.Placemark([lat, lng], {
                hintContent: 'Г. Самара, ул. Ново-Садовая, д. 179',
                balloonContent: 'Г. Самара, ул. Ново-Садовая, д. 179'
            }, {
                iconLayout: 'default#image',
                iconImageHref: iconUrl,
                iconImageSize: [iconW, iconH],
                iconImageOffset: [-halfW, -halfH],
                iconShape: {
                    type: 'Rectangle',
                    coordinates: [
                        [0, 0],
                        [iconW, iconH]
                    ]
                }
            });
            myMap.geoObjects.add(placemark);
            _focusMainStoreOnMobile([lat, lng]);
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
