let customForm = $("form.custom-form-instance");
let filePods = []
customForm.not(":visible").show();

customForm.on("submit", function (event) {
    event.preventDefault();
    ajax_send_custom_form($(this));
});

function ajax_send_custom_form(jquery_form_obj) {
    var token = getCookie("csrftoken");
    jquery_form_obj.find('[name="csrfmiddlewaretoken"]').val(token);
    var data = jquery_form_obj.serialize();

    $.ajax({
        type: "POST",
        url: jquery_form_obj.attr("action"),
        data: new FormData(jquery_form_obj[0]),
        processData: false,
        contentType: false,
        success: function (response) {
            formErrAction(jquery_form_obj, response);
            if (typeof roistat !== "undefined") {
                const obj = jquery_form_obj.serializeArray().reduce((acc, item) => ((acc[item.name] = item.value), acc), {});
                roistat.event.send(`customForm - ${jquery_form_obj.attr("action")}`, obj);
            }
        },
    });
}

function formErrAction(form, response) {
    var msg;
    form.find(".error-text").each(function () {
        $(this).remove();
    });
    form.find(".form-group").each(function () {
        $(this).removeClass("form-group--error");
    });

    if (response.success) {
        form.find("input, textarea").val("");
        $.fancybox.close();
        for (var indexPod = 0; indexPod < filePods.length; indexPod++) {
            var filePond = filePods[indexPod];
            if (filePond.getFiles().length !== 0) {
                for (var i = 0; i <= filePond.getFiles().length - 1; i++) {
                    filePond.removeFile(filePond.getFiles()[0].id);
                }
            }
        }
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
