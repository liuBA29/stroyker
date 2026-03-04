$(document).ready(function () {
    function init_show_filter() {
        $('a.filter-mobile-btn').click(function (e) {
            e.preventDefault();
            $('div.filter-mobile').toggle();
        });
    }

    function init_categories() {
        $('.dropdown-select-ul li').click(function() {
            category_id = $(this).data('value');
            load_data();
        });
    }

    function init_diff_only() {
        $('.radio-f').change(function() {
            diff_only = $(this).val();
            load_data();
        });
    }

    function init_delete() {
        $('a.delete-from-comparison').click(function(e) {
            e.preventDefault();
            var url = $(this).prop('href'),
                product_id = $(this).data('product_id'),
                csrfmiddlewaretoken = $("input[name=csrfmiddlewaretoken]").val();
            $.post(url, {'product_id': product_id, 'csrfmiddlewaretoken': csrfmiddlewaretoken}, function(data) {
                load_data();
                $('#products_comparison_count').text(data.length);
            });
        });
    }

    function init_slider() {
        $('.product-slider--comparison .owl-carousel').owlCarousel({
            loop: true,
            margin: 0,
            nav: true,
            dots: false,
            items: productsCount,
            responsive: {
                0: {
                    items: (productsCount > 2 ? 2 : productsCount)
                },
                992: {
                    items: (productsCount > 3 ? 3 : productsCount)
                }
            }
        });
    }

    function load_data() {
        var send_data = {'category_id': category_id, 'diff_only': diff_only};
        $.get(window.location.href, send_data, function (data) {
            $('div.content-comparison').html(data);

            init_slider();
            init_diff_only();
            init_delete();
            init_show_filter();
            if (typeof initCustomSelect === "function") {
                initCustomSelect();
            }
            init_categories();
        });
    }


    init_slider();
    init_categories();
    init_diff_only();
    init_delete();
    init_show_filter();

});
