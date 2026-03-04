$(document).ready(function () {
    initComarisonButtons();
});

function initComarisonButtons(){
    $('form.product-comparison-form').submit(function(e) {
        e.preventDefault();
        var form = $(this),
            product_id = form.data('product-pk'),
            action = form.prop('action'),
            csrfmiddlewaretoken = form.find('input[name="csrfmiddlewaretoken"]').val(),
            reverse_action = form.data('action-reverse');
        $.post(action, {'product_id': product_id, 'csrfmiddlewaretoken': csrfmiddlewaretoken}, function(data) {
            $('#products_comparison_count').text(data.length);
            var forms = $('form[data-product-pk="' + product_id + '"]');
            forms.prop('action', reverse_action);
            forms.data('action-reverse', action);
            forms.find('.btn-radius--comparison').toggle();
        });
    });
}
