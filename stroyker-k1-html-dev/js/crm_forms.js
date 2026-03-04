function ajax_send_crm_form(form, key, run_onsubmit = false) {
    var data = form.serializeArray();
    $.ajax({
        type: "POST",
        url: form.attr("action"),
        data: data,
        dataType: "json",
    }).done(function (response) {
        formDoneAction(form, response, key);
    });
    if (run_onsubmit && form.hasAttribute("onsubmit")) {
        eval(form.getAttribute("onsubmit")); // jshint ignore:line
    }
}

// feedback message request form handler
//
$("#feedback-message-request-form").on("submit", function (event) {
    event.preventDefault();
    var form = $(this);
    form.find('input[name="url"]').val(window.location.pathname);
    ajax_send_crm_form(form, "feedBackForm");
});

// Вместо того чтобы написать один обработчик для всех тут создан новый как callBack для капчи
function feedback_form_ajax_submit() {
    var form = $("#feedback-message-request-form");
    form.find('input[name="url"]').val(window.location.pathname);
    ajax_send_crm_form(form, 'feedBackForm', true);
}

// call-merequest form handler
$("form.callme-request-form").on("submit", function (event) {
    event.preventDefault();
    ajax_send_crm_form($(this), "callMeForm");
});

function callme_form_ajax_submit(token) {
    let form = $("#crm-callme-request-form");
    ajax_send_crm_form(form, "callMeForm", true);
}

function formDoneAction(form, response, key) {
    var msg;
    form.find(".error-text").each(function () {
        $(this).remove();
    });
    form.find(".form-group").each(function () {
        $(this).removeClass("form-group--error");
    });
    if (response.success) {
        if (typeof roistat !== "undefined") {
            const obj = form.serializeArray().reduce((acc, item) => ((acc[item.name] = item.value), acc), {});
            roistat.event.send(key, obj);
        }
        // дальше очистка полей, без понятия зачем если и так из dom удаляется модалка
        form.find("input, textarea").val("");
        $.fancybox.close();
        msg = response.msg ? response.msg : "<h3>Ваше сообщение отправлено!</h3>";
        $.fancybox.open(msg);
    } else {
        for (var f in response.errors) {
            msg = '<span class="error-text">' + response.errors[f] + "</span>";
            var input = form.find('[name="' + f + '"]');
            var formGroup = input.parent(".form-group");
            formGroup.addClass("form-group--error");
            formGroup.append(msg);
        }
    }
}

// gift for phone form handler
$("form.git-for-phone-form").on("submit", function (event) {
    event.preventDefault();
    var form = $(this);
    var data = form.serializeArray();
    $.ajax({
        type: "POST",
        url: form.attr("action"),
        data: data,
        dataType: "json",
    }).done(function (response) {
        formDoneAction(form, response, "giftForm");
    });
});

// https://redmine.fancymedia.ru/issues/12839
$('input[name="page_url"]').val(window.location.href.split('?')[0]);

const GET_PARAMS = new URLSearchParams(document.location.search);
GET_PARAMS.forEach((value, key) => {
    // Находим все input с заданным name
    const inputs = $('input[name="' + key + '"]');

    inputs.each(function (index, element) {
        const $input = $(element);
        const type = $input.attr('type');

        if (type === 'checkbox' || type === 'radio') {
            // Для чекбоксов и радиокнопок
            if ($input.val() === value) {
                $input.prop('checked', true); // Устанавливаем состояние checked
            } else {
                $input.prop('checked', false); // Снимаем состояние checked
            }
        } else {
            if (index === 0) {
                // Первый input получает значение
                $input.val(value);
            } else {
                // Остальным значения добавляются через атрибут data
                $input.data('value', value);
            }
        }
    });
});