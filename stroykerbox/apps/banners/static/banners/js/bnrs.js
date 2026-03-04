(function ($) {
    $(document).ready(function() {
        var targetImgs = $('.bnr-image-for-page');

        if (BNR_URLS !== 'undefined' && targetImgs.length) {
            targetImgs.each(function( index ) {
                bnrCounterUpd($(this), BNR_URLS.inc_views);
            });

            targetImgs.click(function (e) {
                if($(e.target).closest('a').length){
                    bnrCounterUpd($(this), BNR_URLS.inc_clicks);
                }
            });
        }

    });
})(jQuery);

function bnrCounterUpd(imgElem, updUrl) {
    if (updUrl) {
        pk = imgElem.data('bnr-pk');
        if (pk) {
            $.post(updUrl, {'pk': pk});
        }
    }
}
