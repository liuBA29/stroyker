function onloadFunction() {
    if (!window.smartCaptcha) {
        return;
    }
    document.querySelectorAll('[data-ycaptcha]').forEach((el, index) => {
        let form = el.closest('form');
        if (!form) {
            return;
        }
        let widget = window.smartCaptcha.render(el.id, {
            sitekey: el.dataset.siteKey,
            invisible: el.dataset.useInvisible === 'true',
            shieldPosition: el.dataset.shieldPosition,
            hideShield: el.dataset.hideShield === 'true',
            callback: (token) => {
                // сперва проверка для кастомных форм
                if (form.classList.contains('custom-form-instance')) {
                    // аргумент должен быть jQuery объектом
                    ajax_send_custom_form($(form));
                } else if (el.dataset.submitCallback) {
                    eval(el.dataset.submitCallback + '()')
                } else {
                    form.submit();
                }
            }
        });

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            window.smartCaptcha.execute(widget);
        });
    });

}
