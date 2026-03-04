$(document).ready(function () {
    $('.input-number').each(function () {
        let spinner = $(this),
            input = spinner.find('input[type="number"]'),
            btnUp = spinner.find('.order-up'),
            btnDown = spinner.find('.order-down'),
            min = parseInt(input.attr('min')),
            max = parseInt(input.attr('max')),
            multiplicity = parseInt(input.attr('step')),
            qty;

        if (max === 'inf') {
            max = Infinity;
        }
        btnUp.click(function () {
            qty = parseInt(input.val());
            if (qty > max) {
                input.val(max);
            } else if (qty < max) {
                input.val(qty + multiplicity);
            }
            input.trigger("change");
        });
        input.change(function () {
            qty = parseInt(input.val());
            if (qty > 9 && qty <= 99) {
                btnDown.css('right', 57);
            } else if (qty > 99 && qty <= 999) {
                btnDown.css('right', 74);
            } else if (qty > 999) {
                btnDown.css('right', 90);
            } else {
                btnDown.css('right', 45);
            }
        });
        btnDown.click(function () {
            qty = parseInt(input.val());
            if (qty < min) {
                input.val(min);
            } else if (qty > min) {
                input.val(qty - multiplicity);
            }

            input.trigger("change");
        });
    });
});
