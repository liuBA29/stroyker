const filterForm = $("#catalog_filter_form");

jQuery(document).ready(function ($) {
  updRangeSliders();

  filterForm.on("keyup change paste", "input, select, textarea", function () {
    handleFilterChange(this);
  });

  // Remove empty fields from GET forms
  filterForm.submit(function () {
    var $this = $(this);
    $this
      .find(":input")
      .filter(function () {
        return !this.value;
      })
      .attr("disabled", "disabled");

    prepareFilterForm();
    return true;
  });

  // Un-disable form fields when page loads, in case they click back after submission
  filterForm.find(":input").not(".range-input").prop("disabled", false);

  $(".found-cheaper-panel").on("click", ".close-panel", function () {
    document.cookie = "found_chaper_panel_closed=1; path=/";
  });

  const questionFormBoxId = "question-main";

  $('[href="#' + questionFormBoxId + '"]').click(function () {
    $("html, body").animate(
      {
        scrollTop: $(this.hash).offset().top - 80,
      },
      300,
      function () {}
    );

    var $this = $(this),
      message;
    if ($this.hasClass("smoothScroll")) {
      prepareQestionForm(questionFormBoxId, "Нашли дешевле?", "Где дешевле?");
    } else {
      if ($this.hasClass("not-available")) {
        message =
          $this.attr("data-form-main-msg") ? $this.data("form-main-msg") : "Когда будет в наличии?";
        message += "\n\n" + $this.data("product-name");
        message += '\n"Артикул: ' + $this.data("product-code") + ".";

        prepareQestionForm(questionFormBoxId, $this.data("form-subject"), "Ваш вопрос", message);
      } else if ($this.hasClass("not-price")) {
        message =
          $this.attr("data-form-main-msg") ? $this.data("form-main-msg") : "Хочу узнать цену.";
        message += "\n\n" + $this.data("product-name");
        message += "\nАртикул: " + $this.data("product-code") + ".";
        prepareQestionForm(questionFormBoxId, $this.data("form-subject"), "Ваш вопрос", message);
      }
    }
  });

  function prepareQestionForm(form_id, title, placeholder, message = "") {
    const questionFormBox = $("#" + form_id);
    if (questionFormBox.length) {
      if (title) {
        $(".content-title", questionFormBox).text(title);
      }
      if (placeholder) {
        $('label[for="message"] .content-name', questionFormBox).text(placeholder);
      }
      $("textarea", questionFormBox).text(message);
    }
  }

  // catalog product list sort (mobile mode)
  // Обработчик для кастомного выпадающего списка
  $('.dropdown-select-ul[data-role="products-header-sort-mobile"]').on('click', 'li', function() {
    var selectedValue = $(this).data('value');
    
    if (selectedValue && selectedValue.length > 0) {
      // Получаем текущий URL без параметров
      var currentUrl = window.location.href.split('?')[0];
      
      // Добавляем выбранные параметры сортировки
      var newUrl = currentUrl + selectedValue;
      
      console.log('Redirecting to:', newUrl);
      window.location.href = newUrl;
    }
  });

  // Также оставляем обработчик для настоящего select на случай, если он используется
  $('#products-header-sort-mobile').on('change', function() {
    var selectedValue = $(this).val();
    
    if (selectedValue && selectedValue.length > 0) {
      // Получаем текущий URL без параметров
      var currentUrl = window.location.href.split('?')[0];
      
      // Добавляем выбранные параметры сортировки
      var newUrl = currentUrl + selectedValue;
      
      console.log('Redirecting to:', newUrl);
      window.location.href = newUrl;
    }
  });

  // scroll to target tag
  $('a[rel^="tab"]').click(function () {
    var targetTab = $('.tabs li[rel="' + $(this).attr("rel") + '"]:visible');

    if (!targetTab.length) {
      targetTab = $('.tab_drawer_heading[rel="' + $(this).attr("rel") + '"]:visible');
    }

    if (targetTab.length) {
      $("body,html").animate(
        {
          scrollTop: targetTab.offset().top,
        },
        800 //speed
      );
    }
  });

  $(".view-sort-item").on("click", function () {
    if ($(this).is("[data-list-view-mode]")) {
      Cookies.set("list_view_mode", this.dataset.listViewMode);
    }
  });

  $("#catalog_filter_form input").on("change", (event) => {
    $(event.currentTarget).attr("data-active-input", "");
    console.log("change");
  });

  $("#catalog_filter_form input").on("input", (event) => {
    $(event.currentTarget).attr("data-active-input", "");
    console.log("input");
  });
});

function prepareFilterForm() {
  // clear price_range values
  var rangeInputs = document.querySelectorAll(".range-input");
  rangeInputs.forEach(function (item) {
    if (!item.disabled) {
      item.value = item.value.replace(/[^0-9]+/g, "");
    }
  });
}

function handleFilterChange(elem) {
  var $this = $(elem);

  // Временно отключаем обработчики изменений чтобы избежать рекурсии
  filterForm.off('keyup change paste', 'input, select, textarea');

  filterForm
    .find(":input")
    .not("button")
    .filter(function () {
      if (this.classList.contains("range-input")) {
        return parseInt(this.dataset.initValue) === parseInt(this.value);
      }
      return !this.value;
    })
    .attr("disabled", "disabled");

  prepareFilterForm();

  var formData = filterForm.serialize();
  var url = filterForm.attr("action");
  if (formData.length) {
    url += "?" + formData;
  }

  $.getJSON(url, function (response) {
    var filterShowAll = $(".filter-show-all");
    if (filterShowAll.length > 0) {
      // Убираем предыдущие таймауты для этой кнопки
      filterShowAll.data('timeout-id') && clearTimeout(filterShowAll.data('timeout-id'));
      
      // Всегда показываем кнопку перед обновлением контента
      filterShowAll.stop(true, true).show();
      
      // Обновляем содержимое
      if (response.count && response.count > 0) {
        filterShowAll.html('<a href="' + url + '">Показать ' + response.count + "</a>");
      } else {
        filterShowAll.html('<a href="#">Найдено 0</a>');
      }
      
      // Позиционируем кнопку относительно измененного элемента
      filterShowAll.insertAfter($this.closest('.filter-field, .filter-group').length ? 
                               $this.closest('.filter-field, .filter-group') : $this.parent());
      
      // Устанавливаем новый таймаут для скрытия
      var timeoutId = setTimeout(function () {
        filterShowAll.not(":hover").fadeOut("slow");
      }, 10000);
      
      // Сохраняем ID таймаута для возможности отмены
      filterShowAll.data('timeout-id', timeoutId);
      
      // Обработчик hover для отмены скрытия при наведении
      filterShowAll.off('mouseenter mouseleave').hover(
        function() {
          // При наведении отменяем таймаут скрытия
          clearTimeout($(this).data('timeout-id'));
        },
        function() {
          // При уходе курсора устанавливаем новый таймаут
          var $this = $(this);
          var timeoutId = setTimeout(function() {
            $this.fadeOut("slow");
          }, 2000); // Скрываем через 2 секунды после ухода курсора
          $this.data('timeout-id', timeoutId);
        }
      );
    }
  }).always(function() {
    // Восстанавливаем обработчики после завершения запроса
    setTimeout(function() {
      filterForm.on("keyup change paste", "input, select, textarea", function () {
        handleFilterChange(this);
      });
    }, 100);
  });
}

function updRangeSliders() {
  $(".filter-range").each(function () {
    var filter = this,
      keypressSliders = $(".range-slider");

    $(keypressSliders).each(function (index, keypressSlider) {
      if (keypressSlider !== null && keypressSlider.noUiSlider) {
        var rangeInputs = filter.querySelectorAll(".range-input");
        keypressSlider.noUiSlider.on("update", function () {
          var minInput =
            rangeInputs[0].value.replace(/[^0-9]+/g, "") === rangeInputs[0].dataset.minValue;
          var maxInput =
            rangeInputs[1].value.replace(/[^0-9]+/g, "") === rangeInputs[1].dataset.maxValue;
          for (var i = 0; i < rangeInputs.length; i++) {
            rangeInputs[i].disabled = minInput && maxInput;
          }
        });
        keypressSlider.noUiSlider.on("set", function () {
          handleFilterChange(keypressSlider);
        });
      }
    });
  });
}