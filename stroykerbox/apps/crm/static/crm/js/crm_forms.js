function ajax_send_crm_form(form, key, run_onsubmit = false) {
    var data = form.serializeArray();
    $.ajax({
        type: "POST",
        url: form.attr("action"),
        data: data,
        dataType: "json",
    }).done(function (response) {
        formDoneAction(form, response, key);
    }).fail(function (xhr) {
        formDoneAction(form, { success: false, errors: { __all__: ["Ошибка отправки. Попробуйте позже или позвоните нам."] } }, key);
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

// форма «Остались вопросы?» в футере 8 марта — та же логика, AJAX-отправка.
// Делегирование на document, чтобы сработало и когда скрипт в head грузится раньше футера.
$(document).on("submit", "#feedback-message-request-form-8march", function (event) {
    event.preventDefault();
    var form = $(this);
    form.find('input[name="page_url"]').val(window.location.href.split('?')[0]);
    ajax_send_crm_form(form, "feedBackForm");
});

// форма «Букет по вашим желаниям» (8 марта): делегирование на document, чтобы сработало при любом порядке загрузки; AJAX + дата доставки в текст сообщения
$(document).on("submit", "#feedback-bouquet-wish-form", function (event) {
    event.preventDefault();
    var form = $(this);
    form.find('input[name="page_url"]').val(window.location.href.split('?')[0]);
    var msgEl = form.find('[name="message"]');
    var dateVal = form.find('[name="delivery_date"]').val();
    if (dateVal) {
        msgEl.val('Дата доставки: ' + dateVal + '\n\n' + (msgEl.val() || ''));
    }
    ajax_send_crm_form(form, "feedBackForm");
});

// Вместо того чтобы написать один обработчик для всех тут создан новый как callBack для капчи
function feedback_form_ajax_submit() {
    var form = $("#feedback-message-request-form");
    form.find('input[name="url"]').val(window.location.pathname);
    ajax_send_crm_form(form, 'feedBackForm', true);
}

// Кнопка «ПЕРЕЗВОНИТЕ МНЕ» (8march и др.): явно открываем #callme-modal через Fancybox,
// т.к. при рендере футера через теги авто-привязка Fancybox к [data-fancybox] может не сработать.
$(document).on("click", "a.callme-button[data-src='#callme-modal'], a[data-fancybox='callme-modal'][data-src='#callme-modal']", function (e) {
    e.preventDefault();
    var $modal = $("#callme-modal");
    if ($modal.length && typeof $.fancybox !== "undefined" && $.fancybox.open) {
        $.fancybox.open($modal);
    }
});

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
    form.find(".form-message--success").remove();
    form.find(".form-group").each(function () {
        $(this).removeClass("form-group--error");
    });
    if (response.success) {
        if (typeof roistat !== "undefined") {
            const obj = form.serializeArray().reduce((acc, item) => ((acc[item.name] = item.value), acc), {});
            roistat.event.send(key, obj);
        }
        form.find("input, textarea").val("");
        form.find('input[type="checkbox"]').prop("checked", false);
        msg = response.msg ? response.msg : "Ваше сообщение отправлено!";
        if (typeof $.fancybox !== "undefined" && $.fancybox.open) {
            $.fancybox.close();
            $.fancybox.open("<h3>" + msg + "</h3>");
        } else {
            var wrap = form.closest(".index-bouquet-wish-8march__form-wrap");
            if (wrap.length) {
                wrap.prepend('<p class="form-message--success" style="margin:0 0 0.75rem; color:#2d7a2d;">' + msg + "</p>");
                wrap[0].scrollIntoView({ behavior: "smooth", block: "center" });
            }
        }
    } else {
        if (response.errors) {
            for (var f in response.errors) {
                var errVal = response.errors[f];
                var errText = Array.isArray(errVal) ? errVal.join(" ") : errVal;
                msg = '<span class="error-text">' + errText + "</span>";
                var input = form.find('[name="' + f + '"]');
                var formGroup = input.length ? input.closest(".form-group") : form.find(".form-group").first();
                if (formGroup.length) {
                    formGroup.addClass("form-group--error");
                    formGroup.append(msg);
                }
            }
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
