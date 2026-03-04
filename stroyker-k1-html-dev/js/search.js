$(document).ready(function ($) {
  let clickOuterHandler = null;

  $("[data-search-button]").on("click", (event) => {
    console.log('click');
    const id = $(event.currentTarget).attr("data-search-button");
    const input = $(`[data-search-input="${id}"]`);
    const value = input.val();
    const searchUrl = input.attr("data-search-url");
    window.location = searchUrl + "?q=" + value;
  });

  $("[data-search-input]").on("focus keyup paste", (event) => {
    console.log('focus keyup paste');
    const input = $(event.currentTarget);
    const value = input.val();
    const id = input.attr("data-search-input");
    const searchMinChars = parseInt(input.attr("data-min-chars")) || 0;
    const searchUrl = input.attr("data-search-url");
    const resultContainer = $(`[data-search-results="${id}"]`);
    
    // Удаляем предыдущий обработчик, если он есть
    if (clickOuterHandler) {
      $(document).off("click", clickOuterHandler);
    }
    
    // Создаем новый обработчик для закрытия при клике вне области
    clickOuterHandler = (clickEvent) => {
      if (!clickEvent.target.closest("[data-search-results-active]") && 
          !clickEvent.target.closest("[data-search-input]")) {
        resultContainer.removeAttr("data-search-results-active");
        resultContainer.html("");
        $(document).off("click", clickOuterHandler);
        clickOuterHandler = null;
      }
    };

    if (event.key === "Enter") {
      console.log('Enter');
      // Закрываем результаты перед переходом
      resultContainer.removeAttr("data-search-results-active");
      resultContainer.html("");
      if (clickOuterHandler) {
        $(document).off("click", clickOuterHandler);
        clickOuterHandler = null;
      }
      return (window.location = searchUrl + "?q=" + value)
    }

    // Очищаем результаты если текст слишком короткий или пустой
    if (value.length < searchMinChars) {
      resultContainer.html("");
      resultContainer.removeAttr("data-search-results-active");
      if (clickOuterHandler) {
        $(document).off("click", clickOuterHandler);
        clickOuterHandler = null;
      }
      return;
    }

    try {
      $.ajax({
        type: "get",
        url: searchUrl,
        data: input.serialize(),
        dataType: "html",
      }).done((result) => {
        if (result.replace(/\s/g, "").length <= 0) {
          resultContainer.html("");
          resultContainer.removeAttr("data-search-results-active");
          if (clickOuterHandler) {
            $(document).off("click", clickOuterHandler);
            clickOuterHandler = null;
          }
          return;
        }
        resultContainer.html(result);
        resultContainer.attr("data-search-results-active", "");
        
        // Добавляем обработчик после показа результатов
        setTimeout(() => {
          $(document).on("click", clickOuterHandler);
        }, 0);
      });
    } catch {
      (error) => {
        console.log(error);
      };
    }
  });
});

// мобильный скролл результатов поиска
document.addEventListener('DOMContentLoaded', function() {
    function activateMobileScroll() {
        const searchContainer = document.querySelector('.search-modal-window__search-results');
        if (searchContainer) {
            searchContainer.style.maxHeight = '400px';
            searchContainer.style.overflowY = 'scroll';
            searchContainer.style.webkitOverflowScrolling = 'touch';
            
            searchContainer.addEventListener('touchstart', function(e) {
                e.stopPropagation();
            });
            
            searchContainer.addEventListener('touchmove', function(e) {
                e.stopPropagation();
            });
            
            console.log('Мобильный скролл активирован для:', searchContainer);
        }
    }
    
    // Проверяем каждые 500мс пока не найдем контейнер
    const interval = setInterval(function() {
        activateMobileScroll();
    }, 500);
    
    // Останавливаем через 10 секунд
    setTimeout(function() {
        clearInterval(interval);
    }, 10000);
});