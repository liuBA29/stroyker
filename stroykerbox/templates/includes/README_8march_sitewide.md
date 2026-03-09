# Хэдер и футер 8march: подключение на всех страницах

Сейчас шаблоны `header_8march_standalone.html` и `footer_8march_standalone.html` используются **только на тестовой странице** `/8march_design/` (данные передаются из view через context).

Когда заказчик одобрит дизайн и нужно будет включить хэдер и футер 8march **на всех страницах**:

1. **Включение по флагу (реализовано)**  
   В Constance добавлен флаг `USE_8MARCH_HEADER_FOOTER` (в dev — в `settings/dev.py`, _constance_defaults; по умолчанию `False`).  
   Для продакшена (например, settings заказчика): добавить ключ `USE_8MARCH_HEADER_FOOTER` в CONSTANCE_CONFIG (значение по умолчанию `False`), либо выставить значение в админке Constance после добавления ключа в конфиг.  
   В `base.html`: при включённом флаге подключаются `includes/header_8march.html`, `includes/footer_8march.html`, мобильное меню 8march и модалка «Перезвоните мне» 8march; иначе — текущий хэдер/футер. Восстановление: выставить флаг в False.

2. **Шаблоны для всех страниц**  
   Созданы полные версии:
   - `includes/header_8march.html` — на основе standalone, с `{% location_contact_phone %}`, `{% cart_count_products %}`, config (логотип, SITE_NAME).
   - `includes/footer_8march.html` — на основе standalone, с `{% render_catalog_categories_menu_simple %}`, `{% render_menu 'footer_customer_menu' %}`, `{% location_contact_phone %}`, config.
   - `includes/mobile_bottom_nav_8march.html` — нижнее мобильное меню 8march.

3. **Статика и CSS**  
   При включённом 8march в base подключаются: шрифты эталона, `8march_design/css/8march_base.css`, `8march_design/css/8march_design.css`. На главной (`request.path == '/'`) дополнительно: `8march_index_page_design.css`, flatpickr CSS. Главная при флаге рендерится шаблоном `catalog/frontpage_8march.html` с контентом 8march (герой, категории, акции, букеты, форма «Букет по желаниям» и т.д.).

   **Мини-корзина (опционально):** отдельный файл `8march_design/css/8march_mini_cart.css` и шаблон `includes/mini_cart_8march.html` (подключается из `header_8march.html`). По клику на иконку корзины открывается выдвижная панель с до 2 товаров. Если заказчик не захочет мини-корзину — в файлах есть комментарии, как отключить (удалить подключение CSS в base, убрать include и атрибут у ссылки корзины).

## Чекбоксы согласия (2 шт) и одинаковый текст

Тег `{% render_form_agreement form %}` рендерит `common/tags/form-agreement.html` и может выводить **2 чекбокса**:

- `form_agreement_text` (agree-one)
- `form_agreement_text2` (agree-two, если `agreement2=True` в контексте)

Если в админке/Statictext тексты `form_agreement_text` и `form_agreement_text2` заданы одинаково, визуально получится **2 одинаковых чекбокса** — это не баг в шаблоне, а настройки текста.

Проблем с таким переключением нет: один раз добавляется флаг и два include в base — дальше всё работает для всех страниц.
