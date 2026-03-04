const withVatCheckbox = $('#invoicing-with-vat-input');
withVatCheckbox.hide();

$(document).ready(function () {
    $('input[name=payment_method]').on('change', function () {
        $this = $(this);
        if ($this.val() == 0) {
            withVatCheckbox.show();
        } else {
            withVatCheckbox.hide();
        }
    });


    function toggleExtraFields() {
        let payment_selected = document.querySelector('input[name="payment_method"]:checked');
        let payment_value = parseInt(payment_selected.getAttribute("value"));

        $('.cart-extra-field').each(function (index, element) {
            let element_bind = parseInt(element.getAttribute("binded"));
            if ([payment_value + 5].includes(element_bind)) {
                $(element).show();
            } else {
                $(element).hide();
            }
        })
    }

    $("input[name=payment_method]").click(toggleExtraFields);
    toggleExtraFields();
});
