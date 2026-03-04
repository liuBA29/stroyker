# Хэдер и футер 8march: подключение на всех страницах

Сейчас шаблоны `header_8march_standalone.html` и `footer_8march_standalone.html` используются **только на тестовой странице** `/8march_design/` (данные передаются из view через context).

Когда заказчик одобрит дизайн и нужно будет включить хэдер и футер 8march **на всех страницах**:

1. **Вариант A (рекомендуется)**  
   Добавить в Constance (или в settings) флаг, например `USE_8MARCH_HEADER_FOOTER`.  
   В основном базовом шаблоне сайта (например `base.html`):
   - в блоке header: если флаг включён — `{% include 'includes/header_8march.html' %}`, иначе текущий хэдер;
   - в блоке footer: если флаг включён — `{% include 'includes/footer_8march.html' %}`, иначе текущий футер.

2. **Шаблоны для всех страниц**  
   Создать полные версии с тегами заказчика:
   - `includes/header_8march.html` — на основе `header_8march_standalone.html`, но с `{% render_custom_header_phone %}`, `{% render_catalog_dropdown_menu %}`, `config`, `cart` из context processor и т.д.
   - `includes/footer_8march.html` — на основе `footer_8march_standalone.html`, но с `{% render_catalog_categories_menu_simple %}`, `{% render_menu_footer_split %}`, `{% location_contact_phone %}`, `config` и т.д.

   Эти шаблоны можно взять из проекта luciano-site-light (`custom_headers/header-8march.html`, `includes/footer_8march.html`) и при необходимости подправить пути к статике.

3. **Статика и CSS**  
   На всех страницах при включённом 8march нужно подключать те же стили, что и на тестовой:  
   `8march_design/css/8march_design.css` (и при показе главной — `8march_index_page_design.css`).  
   Это можно делать в base-шаблоне по тому же флагу.

## Чекбоксы согласия (2 шт) и одинаковый текст

Тег `{% render_form_agreement form %}` рендерит `common/tags/form-agreement.html` и может выводить **2 чекбокса**:

- `form_agreement_text` (agree-one)
- `form_agreement_text2` (agree-two, если `agreement2=True` в контексте)

Если в админке/Statictext тексты `form_agreement_text` и `form_agreement_text2` заданы одинаково, визуально получится **2 одинаковых чекбокса** — это не баг в шаблоне, а настройки текста.

Проблем с таким переключением нет: один раз добавляется флаг и два include в base — дальше всё работает для всех страниц.
