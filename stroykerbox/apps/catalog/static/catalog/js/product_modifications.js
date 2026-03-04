jQuery(document).ready(function($){
    $('.product-modification-params select').each( function() {
        $(this).change(function(e) {
            e.preventDefault();
            goToUrl(this.selectedOptions[0]);
        })

    });

    $('.product-modification-params a').each( function() {
        $(this).click(
            function(e) {
                e.preventDefault();
                goToUrl(this);
            }
        )
    });
});


function goToUrl(obj) {
    const formData = new FormData();
    let productInfoObj = obj.closest('[data-ajax-url]');
    if (!productInfoObj) {
        return;
    }

    formData.append('active_id', obj.dataset.paramId);
    formData.append('active_value', obj.dataset.paramValue);
    formData.append('active_datatype', obj.dataset.paramDataType);


    let current = obj;
    document.querySelectorAll('.active[data-param-id]').forEach((el) => {
        if (el.dataset.paramId !== current.dataset.paramId &&
            'paramValue' in el.dataset &&
            obj.dataset.paramDataType === 'str') {
            formData.append(el.dataset.paramId, el.dataset.paramValue);
        }
    });
    console.log(formData)

    fetch(productInfoObj.dataset.ajaxUrl, {
        body: formData,
        method: 'post'
    }).then(response => response.json()).then(data => {
        if (data.url) {
            window.location = data.url;
        }
    });
}
