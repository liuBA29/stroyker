jQuery(document).ready(function($){
    let finalPriceBlock = document.querySelector('.final-price-block');
    let totalSumEl = finalPriceBlock.querySelector('.products-calc-final-price'),
        products = $('.additional-product'),
        calcBtn = finalPriceBlock.querySelector('.related-products-add-to-cart'),
        productPriceMeta = document.querySelector('meta[itemprop="price"]');

    $('.input-number input[type="number"]').on('change', updateRelCalcTotalSum);



    function updateRelCalcTotalSum() {
        productQtyInput = document.querySelector('.shopping-cart-product input');

        let calcSum = 0,
            productSum = 0;

        if (productPriceMeta) {
            productSum = parseFloat(productPriceMeta.content.replace(',', '.'));
        }
        if (productQtyInput) {
            productSum *= productQtyInput.value;
        }


        products.each(function() {
            let input = $('input.product-counter__input', $(this)),
                productPrice = parseFloat(input.data('related-product-price')),
                qty = input.val();
            calcSum += qty * productPrice;
        });

        totalSumEl.innerHTML = (productSum + calcSum).toFixed(2);

        if (calcSum <= 0) {
            calcBtn.classList.add('d-none');
        } else {
            calcBtn.classList.remove('d-none');
        }
    }

    updateRelCalcTotalSum();


    products.each(function() {
        let $this = $(this);
        let productCounter = $('.product-counter', $this);
        let counterUp = $('.product-counter__order-up', $this),
            counterDown = $('.product-counter__order-down', $this),
            qtyInput = $('input.product-counter__input', $this);

        let qtyCurrent = +qtyInput.val()

        counterUp.not('.disabled').on('click', function(e) {
            qtyCurrent += 1;

            productCounter.addClass('product-counter_active');
            qtyInput.val(qtyCurrent);
            updateRelCalcTotalSum();

        })
        counterDown.not('.disabled').on('click', function(e) {
            if (qtyCurrent > 0) {
                qtyCurrent -= 1;
                qtyInput.val(qtyCurrent);
                updateRelCalcTotalSum();
            }
            if (qtyCurrent <= 0) {
                productCounter.removeClass('product-counter_active');
            }
        })
    });

    $('.related-products-add-to-cart').on('click', function(e) {
        e.preventDefault();
        let btn = $(this),
            data = {};

        btn.prop("disabled", true);

        $('.additional-products input[data-product-pk]').each(function() {
            if (this.value !== '0') {
                data[this.dataset.productPk] = +this.value;
            }
        });

        const defaultProduct = $('[data-product-counter]')
        if (defaultProduct.length) {
            const id = defaultProduct.attr('data-product-counter')
            const count = defaultProduct.val();
            data[id] = +count
        }

        if (data) {
            url = btn.data('ajax-url');
            $.post(url, {
                'products': JSON.stringify(data)
            }).done(function(result) {
                if (result.success) {
                    if (result.count) {
                        $('.cart-number').html(result.count);
                    }
                    btn.notify(result.success, 'success');
                }

                else if (result.errors) {
                    btn.notify(result.errors, 'error');

                }
            });
        }

    })
});
