$(document).ready(function() {
    getReadyYandexMap();
});

// управление картой
var autoStore = true;
function getReadyYandexMap() {
    const yamapContainer = $('#yamap_delivery');
    const centerCoords = [
        parseFloat(yamapContainer.data('center-latitude')),
        parseFloat(yamapContainer.data('center-longitude'))
    ];

    if (yamapContainer.length > 0) {
        ymaps.ready(function() {
            var myPlacemark,
                myMap = new ymaps.Map('yamap_delivery', {
                    center: centerCoords,
                    zoom: parseInt(yamapContainer.data('center-zoom'))
                });
            const addressPlace = $("#id_address");

            // слушаем клик на карте
            myMap.events.add('click', function (e) {
                var coords = e.get('coords');
                getRouteByClickOnMap(coords);
            });

            $(document).on('click', '.dropdown-item', function (event) {
                addressTipOnClick($(this));
            });
            // слушаем ввод адреса в input, при вводе адреса производим прямое геокодирование и выводи подсказки
            addressPlace.keyup(function(event){
                if(event.keyCode == 13){
                    event.preventDefault();
                }
            });
            addressPlace.keydown(function(event){
                if(event.keyCode == 13){
                    event.preventDefault();
                }
                // getCoords($(this).val());
            });

            $(document).on('paste', addressPlace, function(event){
                getCoords($(this).val());
            });

            addressPlace.on('input propertychange', function(event) {
                ymaps.suggest($(this).val()).then(
                    function (items) {
                        // items - массив поисковых подсказок.
                        result = '';
                        $(items).each( function (index) {
                            result += ('<li class="dropdown-item">'+items[index].displayName+'</li>');
                        });
                        $('#addressTips').css('display', 'block').html(result);
                    },
                    function (err) {
                        // обрабатываем ошибку
                        console.error(err.message)
                        var msg = 'Некорректно выбран адрес, укажите точку на карте';
                        $('.form-delivery-address').html('<span style="color: red">' + msg + '<span>');
                    });
            });

            // слушаем ввод адреса в store_select
            var stockField = $('.dropdown-select-ul[data-role="id_stock"]');
            stockField.on('DOMSubtreeModified', 'li.selected', function(event) {
                $('select[name=stock]').val($(this).data('value'));
                autoStore = false;
                if (myPlacemark) {
                    var coords = myPlacemark.geometry.getCoordinates();
                    getRouteByClickOnMap(coords);
                }
            });

            // реакция на изменения типа авто
            var carField = $('.dropdown-select-ul[data-role="id_car"]');
            carField.on('DOMSubtreeModified', 'li.selected', function(event) {
                $('select[name=car]').val($(this).data('value'));
                recalculateDeliveryCost();
            });

            // при потере фокуса полем адреса скрываем подсказки
            $('#id_address').on('blur', function(event) {
                if (!$('#addressTips').is(':hover')) {
                    $('#addressTips').css('display', 'none');
                }
            });
            // при наведении фокуса показываем предыдушие подсказки если поле не пустое
            $('#id_address').on('focus', function(event) {
                if ($(this).val().length > 0) {
                    $('#addressTips').css('display', 'block');
                }
            });

            var address = $('#id_address').val();
            if (address) {
                getCoords(address);
            }




            function getRouteByClickOnMap(coords) {
                // Если метка уже создана – просто передвигаем ее
                if (myPlacemark) {
                    myPlacemark.geometry.setCoordinates(coords);
                }
                // Если нет – создаем
                else {
                    myPlacemark = createPlacemark(coords);
                    myMap.geoObjects.add(myPlacemark);
                    // Слушаем событие окончания перетаскивания на метке.
                    myPlacemark.events.add('dragend', function () {
                        getAddress(myPlacemark.geometry.getCoordinates());
                    });
                }
                getAddress(coords);
            }


            // обработчик клика по подсказке
            function addressTipOnClick(tip) {
                const address = tip.html();
                $('#id_address').val(address);
                $('#id_address').focus();
                $('#addressTips').css('display', 'none');
                getCoords(address);
            }


            // Создание метки
            function createPlacemark(coords) {
                return new ymaps.Placemark(coords, {
                    iconCaption: 'поиск...'
                }, {
                    preset: 'islands#blueDotIconWithCaption',
                    draggable: true
                });
            }


            // Определяем координаты по адресу (прямое геокодирование)
            function getCoords(address) {
                ymaps.geocode(address, {
                    /**
                     * Опции запроса
                     * @see https://api.yandex.ru/maps/doc/jsapi/2.1/ref/reference/geocode.xml
                     */
                    // Сортировка результатов от центра окна карты.
                    // boundedBy: myMap.getBounds(),
                    // strictBounds: true,
                    // Вместе с опцией boundedBy будет искать строго внутри области, указанной в boundedBy.
                    // Если нужен только один результат, экономим трафик пользователей.
                    results: 1
                }).then(function (res) {
                    $('.delivery_address__input_error__message').remove();
                    $('.btn-order-next').removeAttr('disabled');
                    // Выбираем первый результат геокодирования.
                    var firstGeoObject = res.geoObjects.get(0);
                    // проверка точности адреса.
                    var error = null;
                    if (typeof firstGeoObject === 'undefined') {
                        error = 'Неточный адрес, возможно, неверно указан город';
                    } else {
                        switch (firstGeoObject.properties.get('metaDataProperty.GeocoderMetaData.precision')) {
                            case 'exact':
                                break;
                            case 'number':
                            case 'near':
                            case 'range':
                            case 'street':
                                error = 'Неполный адрес, уточните номер дома';
                                break;
                            default:
                                error = 'Неточный адрес, требуется уточнение';
                        }
                    }
                    if (error) {
                        if (myMap.geoObjects.getLength()) myMap.geoObjects.removeAll();
                        var message = '<p class="delivery_address__input_error__message text-danger m-0">'+error+'</p>';
                        $('#id_address').after(message);
                        $('.btn-order-next').attr('disabled', 'true');
                        return;
                    }
                    // Координаты геообъекта.
                    coords = firstGeoObject.geometry.getCoordinates();
                    // Передаем координаты в форму заказа
                    $('input[name="address_lat"]').val(Number(coords[0]).toPrecision(9));
                    $('input[name="address_long"]').val(Number(coords[1]).toPrecision(9));

                    // Если метка уже создана – просто передвигаем ее
                    if (myPlacemark) {
                        myPlacemark.geometry.setCoordinates(coords);
                    } else {
                        // Если нет – создаем
                        myPlacemark = createPlacemark(coords);
                        myMap.geoObjects.add(myPlacemark);
                        // Слушаем событие окончания перетаскивания на метке.
                        myPlacemark.events.add('dragend', function () {
                            getAddress(myPlacemark.geometry.getCoordinates());
                        });
                    }

                    addRoute(coords, myMap, address);
                    autoStore = true;

                }, function(err) {
                    console.log("Error: " + error.message);
                });
            }

            // Определяем адрес по координатам (обратное геокодирование)
            function getAddress(coords) {
                myPlacemark.properties.set('iconCaption', 'поиск...');
                ymaps.geocode(coords).then(function (res) {
                    const firstGeoObject = res.geoObjects.get(0);
                    const addressLine = firstGeoObject.getAddressLine();

                    // направляем полученный адрес в поле формы
                    if ($('[id="id_address"]').length > 0) {
                        $('[id="id_address"]').val(addressLine);
                    }
                    // Передаем координаты в форму заказа
                    $('input[name="address_latitude"]').val(Number(coords[0]).toPrecision(9));
                    $('input[name="address_longitude"]').val(Number(coords[1]).toPrecision(9));

                    addRoute(coords, myMap, addressLine);
                    autoStore = true;
                });
            }

        });
    }
}

function recalculateDeliveryCost(routeLengthKm, ajax=true) {
    var address = $("#id_address"),
        err_msg = null;
    $('.delivery_address__input_error__message').remove();

    if (!routeLengthKm) {
        routeLengthKm = $('input[name="distance_km"]').val()
    } else {
        $('input[name="distance_km"]').val(routeLengthKm);
    }

    if (!address.val()){
        err_msg = 'Укажите точку на карте';

    } else if (!routeLengthKm) {
        err_msg = 'Не удалось определить расстояние';
    }

    if (err_msg) {
        $('.form-delivery-address').html(
            '<div style="color:red;text-align:right">'
            + err_msg
            + '</div>');
        return;

    }

    if (ajax) {
        var deliveryTypeId = $('[name="delivery_type"]:checked').val(),
            deliveryTypeForm = $('#delivery_form_' + deliveryTypeId),
            car_pk = $('select[name="car"]').val();

        $('.form-delivery-distance', deliveryTypeForm)
            .html('Расчитанное расстояние: <span>'+ routeLengthKm +' км.</span>');

        if (!car_pk) return;

        var url = $('.calculate-delivery__form-delivery', deliveryTypeForm).attr('data-delivery-cost-url');

        var data = {};
        data.car_pk = car_pk;
        data.route_length_km = routeLengthKm;

        $.ajax({
            method: 'GET',
            url: url,
            data: data,
            dataType: 'json'
        }).done(function(result) {
            if (address) {
                $('.form-delivery-address',
                    deliveryTypeForm).html(
                        '<div style="font-size: 18px;margin-bottom:11px">'
                        + address.val()
                        + '</div>');
            }

            $('input[name="delivery_cost"]', deliveryTypeForm)
                .val(parseFloat(result.delivery_cost).toFixed(2).toString());

            $('.form-delivery-cost', deliveryTypeForm)
                .html('Стоимость доставки: <span>' + Math.round(parseFloat(result.delivery_cost)
                    .toFixed(2).toString()) +' ₽</span>');
            $('.form-delivery-cost-num', deliveryTypeForm)
                .html(parseFloat(result.delivery_cost).toFixed(2).toString() + ' ₽');

            $('.whole_cost', deliveryTypeForm)
                .html('Итого с доставкой: '+ parseFloat(result.cost_with_delivery)
                    .toFixed(2).toString() +' ₽');
            $('.whole_cost_num', deliveryTypeForm)
                .html(parseFloat(result.cost_with_delivery).toFixed(2).toString() + ' ₽');
        });
    }
}

// getting the length of the route
function addRoute(coords, map, destAddressLine) {
    var stockVal = $('#id_stock option:selected').html();
    if (!stockVal.replace('-', '')) return;

    ymaps.route([
        stockVal,
        { type: 'wayPoint', point: coords }
    ], {
        mapStateAutoApply: true
    }).then(function (route) {

        // balloon content for shipping address
        route.getWayPoints().get(1).properties.set({
            'balloonContent': destAddressLine,
        });

        routeLengthKm = Math.ceil(route.getLength() / 1000);
        $('input[name="distance_km"]').val(routeLengthKm);
        recalculateDeliveryCost(routeLengthKm);

        if (map.geoObjects.getLength()) map.geoObjects.removeAll();

        // добавляем маршрут на карту
        map.geoObjects.add(route);
        map.setBounds(route.getBounds(), {checkZoomRange:true});
    });
}


