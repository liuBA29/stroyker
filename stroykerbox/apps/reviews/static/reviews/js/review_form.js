$(document).ready(function () {

    /* 1. Visualizing things on Hover - See next part for action on click */
    $('#stars li').on('mouseover', function () {
        var onStar = parseInt($(this).data('value'), 10); // The star currently mouse on

        // Now highlight all the stars that's not after the current hovered star
        $(this).parent().children('li.star').each(function (e) {
            if (e < onStar) {
                $(this).addClass('hover');
            } else {
                $(this).removeClass('hover');
            }
        });

    }).on('mouseout', function () {
        $(this).parent().children('li.star').each(function (e) {
            $(this).removeClass('hover');
        });
    });


    /* 2. Action to perform on click */
    $('#stars li').on('click', function () {
        var onStar = parseInt($(this).data('value'), 10); // The star currently selected
        var stars = $(this).parent().children('li.star');

        for (i = 0; i < stars.length; i++) {
            $(stars[i]).removeClass('selected');
        }

        for (i = 0; i < onStar; i++) {
            $(stars[i]).addClass('selected');
        }

        var ratingField = $('input#id_rating_value');
        if (ratingField) {
            var ratingValue = parseInt($('#stars li.selected').last().data('value'), 10);
            ratingField.val(ratingValue);
        }

    });


});

$(document).on('click', '.review__footer__yes', function(event) {
    event.preventDefault();
    var self = $(this);
    getAdvantage(self);
});

$(document).on('click', '.review__footer__no', function(event) {
    event.preventDefault();
    var self = $(this);
    getAdvantage(self);
});

function getAdvantage(self) {
    review_adv = self.siblings('.review_advantage')[0];
    url = self.data('url');
    $.ajax({
        type: 'GET',
        url: url,
    }).done(function(result) {
        if(result.success) {
            $(review_adv).html(result.advantage);
        } else if (result.errors) {
            $(review_adv).notify(result.errors);
        }
    });
}

$('form#review_form').submit(function(event) {
    event.preventDefault();

    var $form = $(this),
        url = $form.attr( "action" );

    $.post(url, {
        'review_text': $form.find("textarea[name='review_text']").val(),
        'rating_value': $form.find("input[name='rating_value']").val()
    }).done(function(response) {
        if (response.success && response.message) {
            $form.siblings('.rate-product').hide();
            $form.html('<p class="success-message">' + response.message + '</p>');

        } else if (response.errors) {
            var message;
            if ($.type(response.errors) === "string") {
                message = response.errors;
            } else {
                var fields = {'review_text': 'Текст отзыва', 'rating_value': 'Рейтинг'};
                message = 'Пожалуйста, исправьте ошибки: \n\n';
                messageStatus = 'error';
                if ('__all__' in response.errors) {
                    message = response.errors.__all__.join(', ');
                } else {
                    for (var f in response.errors) {
                        message += fields[f] + ': ' + response.errors[f].join(', ') + '\n';
                    }
                }
            }
            $form.find(':submit').notify(message, 'error', { position: "right" });
        }
    });
});

