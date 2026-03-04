import jQuery from "jquery";
import wNumb from "wnumb";
import noUiSlider from "nouislider";
import tippy from "tippy.js";
import "owl.carousel";
import "mmenu-js";
import "slick-carousel";
import "@fancyapps/fancybox";
import "inputmask/dist/jquery.inputmask.js";
import { initShared } from "../../shared";
import { initComponents } from "../../components";

window.wNumb = wNumb;
window.noUiSlider = noUiSlider;
window.tippy = tippy;

window.breakpoints = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 1024,
  xl: 1280,
};

$(() => {
  initShared();
  initComponents();
});

const $compareCarousel = $(".owl-carousel--compare")
const $detailCarousel = $(".owl-carousel--detail")

if ($compareCarousel.length && $detailCarousel.length) {
  const $pagination = $(".owl-pagination--compare")
  const $counter = $pagination.find(".counter")
  const $prev = $pagination.find(".prev")
  const $next = $pagination.find(".next")

  function updatePagination(event) {
    const itemsPerPage = event.page.size // Количество слайдов на странице
    const totalItems = event.item.count  // Всего слайдов
    const startIndex = event.item.index + 1 // Номер первого отображаемого слайда
    const endIndex = Math.min(startIndex + itemsPerPage - 1, totalItems) // Номер последнего отображаемого слайда

    // Обновляем текст пагинации
    $counter.text(`${startIndex}-${endIndex}/${totalItems}`)

    // Проверяем, первый ли это слайд
    if (event.item.index === 0) { // Начало слайдера
      $prev.prop("disabled", true).attr("inert", "")
    } else {
      $prev.prop("disabled", false).removeAttr("inert")
    }

    // Проверяем, последний ли это слайд
    const isLastPage = event.item.index + itemsPerPage >= totalItems
    if (isLastPage) { // Конец слайдера
      $next.prop("disabled", true).attr("inert", "")
    } else {
      $next.prop("disabled", false).removeAttr("inert")
    }
  }

  // Инициализация Owl Carousel
  $compareCarousel.owlCarousel({
    items: 4,
    margin: 0,
    nav: false,
    dots: false,
    responsive: {
      0: {
        items: 2,
        margin: 0,
      },
      992: {
        items: 4,
        margin: 0,
      }
    },
    onInitialized: updatePagination, // Обновить пагинацию при инициализации
    onTranslated: updatePagination   // Обновить пагинацию при смене слайдов
  })

  $detailCarousel.owlCarousel({
    items: 4,
    margin: 0,
    nav: false,
    dots: false,
    responsive: {
      0: {
        items: 2,
        margin: 0,
      },
      992: {
        items: 4,
        margin: 0,
      }
    }
  })

  function updateFirstVisibleClass(carousel) {
    // Удаляем класс со всех элементов
    carousel.find('.owl-item').removeClass('owl-active-first')

    // Находим текущие видимые элементы
    const visibleItems = carousel.find('.owl-item.active')

    // Добавляем класс только к первому
    if (visibleItems.length) {
      visibleItems.first().addClass('owl-active-first')
    }
  }

  // Синхронизация двух каруселей
  function syncCarousels(event) {
    const targetIndex = event.item.index
    const syncedCarousel = event.currentTarget === $compareCarousel[0]
      ? $detailCarousel
      : $compareCarousel

    syncedCarousel.trigger('to.owl.carousel', [targetIndex, 300, true])
  }

  $compareCarousel.on('changed.owl.carousel', syncCarousels)
  $detailCarousel.on('changed.owl.carousel', syncCarousels)

  // Добавляем класс после инициализации
  updateFirstVisibleClass($detailCarousel)

  // Добавляем класс при изменении активного слайда
  $detailCarousel.on('changed.owl.carousel', function () {
    setTimeout(() => updateFirstVisibleClass($detailCarousel));
  })

  // Кнопки навигации
  $prev.on("click", function () {
    $compareCarousel.trigger("prev.owl.carousel")
    $detailCarousel.trigger("prev.owl.carousel")
  })

  $next.on("click", function () {
    $compareCarousel.trigger("next.owl.carousel")
    $detailCarousel.trigger("next.owl.carousel")
  })

  function setEqualHeights() {
    const allProducts = document.querySelectorAll('.detail-product')

    // Сбрасываем высоты перед пересчётом
    allProducts.forEach(product =>
      Array.from(product.children).forEach(item => (item.style.minHeight = ''))
    )

    const maxItems = Math.max(...Array.from(allProducts).map(product => product.children.length))

    // Пройдём по каждому индексу
    for (let i = 0; i < maxItems; i++) {
      const heights = []

      // Собираем высоты всех элементов с текущим индексом
      allProducts.forEach(product => {
        const item = product.children[i]
        if (item) heights.push(item.offsetHeight)
      })

      // Определяем максимальную высоту
      const maxHeight = Math.max(...heights)

      // Устанавливаем максимальную высоту для всех элементов с этим индексом
      allProducts.forEach(product => {
        const item = product.children[i]
        if (item) item.style.minHeight = `${maxHeight}px`
      })
    }
  }

  const throttle = (func, delay = 300) => {
    let isThrottled = false;
    let savedArgs = null;
    let savedThis = null;

    return function wrap(...args) {
      if (isThrottled) {
        savedArgs = args,
          savedThis = this;
        return;
      }

      func.apply(this, args);
      isThrottled = true;

      setTimeout(() => {
        isThrottled = false;

        if (savedThis) {
          wrap.apply(savedThis, savedArgs);
          savedThis = null;
          savedArgs = null;
        }

      }, delay);
    }
  };

  // Добавляем обработчик события resize
  window.addEventListener('resize', throttle(() => {
    setTimeout(setEqualHeights, 300)
  }))

  // Инициализация при загрузке
  setEqualHeights()
}

$(".acc__toggle:not(.not_toggle)").click(function (e) {
  // e.preventDefault();

  var $this = $(this);
  if ($this.next().hasClass("show")) {
    $this.next().removeClass("show");
    $this.removeClass("active");
    $this.next().slideUp(200);
  } else {
    $this.parent().parent().find("li .inner").removeClass("show");
    $this.parent().parent().find("li .acc__toggle").removeClass("active");
    $this.parent().parent().find("li .inner").slideUp(200);
    $this.next().toggleClass("show");
    $this.toggleClass("active");
    $this.next().slideToggle(200);
  }
});

var bigSlides = $(".main-slider .owl-carousel"),
  autoPlayTimeoutSec = parseInt(bigSlides.data("autoplay-timeout"));
bigSlides.owlCarousel({
  loop: true,
  margin: 5,
  nav: true,
  dots: true,
  items: 1,
  autoplay: true,
  autoplayTimeout: autoPlayTimeoutSec * 1000,
  navText: [
    '<svg class="icon" viewBox="0 0 10.5 18.1"><path stroke="none" d="M9,0l1.4,1.4L2.8,9l7.6,7.6L9,18.1L0,9C0,9,9.1,0,9,0z"></path></svg>',
    '<svg class="icon" viewBox="0 0 10.5 18.1"><path stroke="none" d="M1.4,18.1L0,16.7l7.6-7.6L0,1.5L1.4,0l9,9.1C10.4,9.1,1.3,18.1,1.4,18.1z"></path></svg>',
  ],
});
var radioButtons = document.querySelectorAll('.delivery-selection input[type="radio"]');
var choices = document.querySelectorAll(".delivery-choice");
radioButtons.forEach(function (btn) {
  btn.addEventListener("change", function () {
    var clicked = this;
    choices.forEach(function (choice) {
      if (choice.classList.contains(clicked.id) || choice.classList.contains("delivery-type-" + clicked.value)) {
        choice.style.display = "block";
      } else {
        choice.style.display = "none";
      }
    });
  });
});
$(".shopping-cart-item__delete").click(function () {
  $(this).parent(".shopping-cart-item").remove();
});
$(".slider .owl-carousel").owlCarousel({
  loop: true,
  margin: 10,
  items: 1,
  nav: true,
});
$(".news-slider .owl-carousel").owlCarousel({
  loop: true,
  margin: 10,
  items: 4,
  responsive: {
    0: {
      nav: false,
      dots: true,
      items: 1,
    },
    479: {
      nav: false,
      dots: true,
      items: 2,
    },
    768: {
      nav: true,
      dots: false,
      items: 3,
    },
    992: {
      items: 4,
    },
  },
});
$(".action-slider .owl-carousel").owlCarousel({
  loop: true,
  margin: 20,
  nav: true,
  dots: false,
  items: 3,
  responsive: {
    0: {
      nav: false,
      dots: true,
      items: 1,
    },
    479: {
      nav: false,
      dots: true,
      items: 2,
    },
    768: {
      nav: true,
      dots: false,
      items: 3,
    },
  },
});
$(".partners-slider .owl-carousel").owlCarousel({
  loop: true,
  margin: 10,
  nav: true,
  dots: false,
  items: 5,
  responsive: {
    0: {
      dots: true,
      nav: false,
      items: 1,
    },
    566: {
      nav: false,
      dots: true,
      items: 2,
    },
    768: {
      nav: false,
      dots: true,
      items: 3,
    },
    900: {
      nav: false,
      dots: true,
      items: 4,
    },
    950: {
      dots: false,
    },
  },
});

(() => {
  const buttonDefaultView = $(".button1");
  const buttonWideView = $(".button2");
  const buttonLineView = $(".button3");
  const items = $(".product-item");

  buttonWideView.click((event) => {
    buttonDefaultView.removeClass("current");
    buttonLineView.removeClass("current");
    $(event.currentTarget).addClass("current");
    localStorage.setItem("catalogGrid", "wide");
    items.removeClass("product-item--line");
    items.addClass("product-item--wide");
  });

  buttonLineView.click((event) => {
    buttonWideView.removeClass("current");
    buttonDefaultView.removeClass("current");
    $(event.currentTarget).addClass("current");
    localStorage.setItem("catalogGrid", "wide");
    items.removeClass("product-item--wide");
    items.addClass("product-item--line");
  });

  buttonDefaultView.click((event) => {
    buttonWideView.removeClass("current");
    buttonLineView.removeClass("current");
    $(event.currentTarget).addClass("current");
    localStorage.setItem("catalogGrid", "default");
    items.removeClass("product-item--wide");
    items.removeClass("product-item--line");
  });
})();

$(document).ready(function () {
  $(document).on("click", (event) => {
    if (!event.target.closest(".bottom-mobile-menu") && $(".bottom-mobile-menu-list_active")) {
      $(".bottom-mobile-menu-list_active").removeClass("bottom-mobile-menu-list_active");
      $(".bottom-mobile-menu-button_active").removeClass("bottom-mobile-menu-button_active");
    }
  });

  $(".catalog-filter-accordion a.opener").click(function () {
    $(this).parent().find("ul:first").slideToggle();
    $(this).parent().toggleClass("active");
    return false;
  });

  $("[data-open-dropdown-content]").on("click", (event) => {
    const target = $(event.currentTarget);
    const parent = target.parent();
    parent.find("[data-close-dropdown-content]").removeClass("d-none");
    target.addClass("d-none");
  });

  $("[data-close-dropdown-content]").on("click", (event) => {
    const target = $(event.currentTarget);
    const parent = target.parent();
    parent.find("[data-open-dropdown-content]").removeClass("d-none");
    target.addClass("d-none");
  });

  $("[data-toggle-bottom-dropdown]").on("click", (event) => {
    $(".bottom-mobile-menu-list").toggleClass("bottom-mobile-menu-list_active");
    $(event.currentTarget).toggleClass("bottom-mobile-menu-button_active");
  });

  $("[data-close-search-modal]").on("click", () => {
    $(".search-modal-window").removeClass("d-block");
  });

  $("[data-open-search-modal]").on("click", () => {
    $(".search-modal-window").addClass("d-block");
    $(".search-modal-window__input").focus();
  });

  $("[data-clear-input-button]").on("click", (event) => {
    const id = $(event.currentTarget).attr("data-clear-input-button");
    $(`[data-clear-input="${id}"]`).val("");
  });

  $(".like-btn").on("click", function (event) {
    event.preventDefault();
    $(this).toggleClass("active");
  });
  $(".city-selection__link").click(function () {
    $(".city-selection__list").toggle(0);
  });
  $(window).click(function (e) {
    if (!e.target.classList.contains("city-selection__link")) {
      $(".city-selection__list").toggle(false);
    }
  });
  $(".burger-menu").click(function () {
    $(".mobile-menu").toggle(0);
  });
  $(".catalog-inner-btn").click(function (e) {
    e.preventDefault();
    $(this).toggleClass("open");
    $(".catalog-header-content").toggle(0);
  });
  $(".catalog-inner-btn,.catalog-menu__head a").click(function (e) {
    e.preventDefault();
    $(".catalog-menu").toggle(0);
  });
  $(".burger-catalog").click(function (e) {
    e.preventDefault();
    $(this).toggleClass("open");
  });
  $(".share-btn").click(function () {
    $(".share-block__show").toggle(0);
  });
  $(".close-panel").click(function () {
    $(".bottom-panel").toggle(0);
  });
  $(".filter-btn, .close-btn-2").click(function () {
    $(".catalog-filter").toggle(0);
  });
  $(".catalog-side__title").click(function () {
    $(".catalog-side__content").toggle(0);
    $(".catalog-side__content-accordeon").toggle(0);
  });
  $(".catalog-opened").click(function () {
    $(".catalog-opened .submenu").toggle(0);
  });
  $(".burger-menu").click(function () {
    $(this).toggleClass("menu-on");
  });
  $(".catalog-inner").click(function () {
    $(this).toggleClass("open");
    $(".catalog-inner-content").toggle(0);
  });
});

function gallery() {
  if ($.fancybox) {
    $(".owl-item [data-fancybox]").on("click", function () {
      var $selector = $(this).parents(".owl-carousel").find(".owl-item:not(.cloned) [data-fancybox]");
      $.fancybox.open(
        $selector,
        {
          selector: $selector,
          backFocus: false,
        },
        $selector.index(this)
      );
      return false;
    });
  }
}

function header() {
  var $header = $("header"),
    height,
    scroll;
  let isThrottled = false;
  check();
  $(window).scroll(function () {
    if (isThrottled) return;
    isThrottled = true;
    setTimeout(() => {
      check();
      isThrottled = false;
    }, 100);
  });

  function check() {
    if (!$header.hasClass("header_landing")) {
      scroll = $(window).scrollTop();
      height = $header.height();

      if (scroll > height) {
        $header.addClass("fixed");
      } else {
        $header.removeClass("fixed");
      }
    }
  }
} //gallery

function homeBanner() {
  var $slider = $(".home-banner .owl-carousel"),
    arrowPrev =
      '<svg class="icon" viewBox="0 0 10.5 18.1"><path stroke="none" d="M9,0l1.4,1.4L2.8,9l7.6,7.6L9,18.1L0,9C0,9,9.1,0,9,0z"></path></svg>',
    arrowNext =
      '<svg class="icon" viewBox="0 0 10.5 18.1"><path stroke="none" d="M1.4,18.1L0,16.7l7.6-7.6L0,1.5L1.4,0l9,9.1C10.4,9.1,1.3,18.1,1.4,18.1z"></path></svg>';

  if ($slider.length) {
    $slider.owlCarousel({
      loop: true,
      nav: true,
      smartSpeed: 500,
      dots: true,
      items: 1,
      lazyLoad: true,
      autoplay: true,
      autoplayTimeout: (+$slider.data("autoplay-timeout") || 5) * 1000,
      navText: [arrowPrev, arrowNext],
      autoplayHoverPause: true,
    });
  }
}

$(document).ready(() => {
  const keypressSliders = $(".range-slider");
  $(keypressSliders).each(function (index, keypressSlider) {
    const field_name = $(keypressSlider).data("name");
    const input0 = document.getElementById("id_" + field_name + "_0");
    const input1 = document.getElementById("id_" + field_name + "_1");
    const inputs = [input0, input1];

    const startVal = input0 ? parseInt(input0.dataset.currentValue) : undefined;
    const endVal = input1 ? parseInt(input1.dataset.currentValue) : undefined;
    const minVal = input0 ? parseInt(input0.dataset.minValue) : undefined;
    const maxVal = input1 ? parseInt(input1.dataset.maxValue) : undefined;

    let postfix = "";

    if (field_name == "price_range") {
      postfix = " ₽";
    }

    if (typeof noUiSlider !== "undefined") {
      noUiSlider.create(keypressSlider, {
        start: [startVal, endVal],
        connect: true,
        range: {
          min: minVal,
          max: maxVal,
        },
        format: wNumb({
          decimals: 0,
          thousand: " ",
          postfix: postfix,
        }),
        step: 1,
      });
    }

    if (keypressSlider !== null && keypressSlider.noUiSlider) {
      keypressSlider.noUiSlider.on("update", function (values, handle) {
        inputs[handle].value = values[handle];
      });
    }

    function setSliderHandle(i, value) {
      let r = [null, null];
      r[i] = value;
      keypressSlider.noUiSlider.set(r);
    } // Listen to keydown events on the input field.

    inputs.forEach(function (input, handle) {
      if (input === null) return;
      input.addEventListener("change", function () {
        setSliderHandle(handle, this.value);
      });
      input.addEventListener("keydown", function (e) {
        let values = keypressSlider.noUiSlider.get();
        let value = Number(values[handle]); // [[handle0_down, handle0_up], [handle1_down, handle1_up]]

        let steps = keypressSlider.noUiSlider.steps(); // [down, up]

        let step = steps[handle];
        let position; // 13 is enter,
        // 38 is key up,
        // 40 is key down.

        switch (e.which) {
          case 13:
            setSliderHandle(handle, this.value);
            break;

          case 38:
            // Get step to go increase slider value (up)
            position = step[1]; // false = no step is set

            if (position === false) {
              position = 1;
            } // null = edge of slider

            if (position !== null) {
              setSliderHandle(handle, value + position);
            }

            break;

          case 40:
            position = step[0];

            if (position === false) {
              position = 1;
            }

            if (position !== null) {
              setSliderHandle(handle, value - position);
            }

            break;
        }
      });
    });
  });
});

$(function () {
  // This will select everything with the class smoothScroll
  // This should prevent problems with carousel, scrollspy, etc...
  $(".smoothScroll").click(function () {
    if (
      location.pathname.replace(/^\//, "") == this.pathname.replace(/^\//, "") &&
      location.hostname == this.hostname
    ) {
      var target = $(this.hash);
      target = target.length ? target : $("[name=" + this.hash.slice(1) + "]");

      if (target.length) {
        $("html,body").animate(
          {
            scrollTop: target.offset().top,
          },
          1000
        ); // The number here represents the speed of the scroll in milliseconds

        return false;
      }
    }
  });
});

$(document).ready(function () {
  var sync1 = $("#sync1");
  var sync2 = $("#sync2");
  var slidesPerPage = 3; //globaly define number of elements per page

  var syncedSecondary = true;
  sync1
    .owlCarousel({
      items: 1,
      slideSpeed: 2000,
      nav: true,
      autoplay: false,
      dots: true,
      loop: true,
      responsiveRefreshRate: 200,
      margin: 10,
    })
    .on("changed.owl.carousel", syncPosition);
  sync2
    .on("initialized.owl.carousel", function () {
      sync2.find(".owl-item").eq(0).addClass("current");
    })
    .owlCarousel({
      items: slidesPerPage,
      dots: true,
      nav: true,
      margin: 10,
      smartSpeed: 200,
      slideSpeed: 500,
      slideBy: slidesPerPage,
      //alternatively you can slide by 1, this way the active slide will stick to the first item in the second carousel
      responsiveRefreshRate: 100,
    })
    .on("changed.owl.carousel", syncPosition2);

  function syncPosition(el) {
    //if you set loop to false, you have to restore this next line
    //var current = el.item.index;
    //if you disable loop you have to comment this block
    var count = el.item.count - 1;
    var current = Math.round(el.item.index - el.item.count / 2 - 0.5);

    if (current < 0) {
      current = count;
    }

    if (current > count) {
      current = 0;
    } //end block

    sync2.find(".owl-item").removeClass("current").eq(current).addClass("current");
    var onscreen = sync2.find(".owl-item.active").length - 1;
    var start = sync2.find(".owl-item.active").first().index();
    var end = sync2.find(".owl-item.active").last().index();

    if (current > end) {
      sync2.data("owl.carousel").to(current, 100, true);
    }

    if (current < start) {
      sync2.data("owl.carousel").to(current - onscreen, 100, true);
    }
  }

  function syncPosition2(el) {
    if (syncedSecondary) {
      var number = el.item.index;
      sync1.data("owl.carousel").to(number, 100, true);
    }
  }

  sync2.on("click", ".owl-item", function (e) {
    e.preventDefault();
    var number = $(this).index();
    sync1.data("owl.carousel").to(number, 300, true);
  });
});

$(".tab-content").hide();
$(".tab-content:first").show();
/* if in tab mode */

$("ul.tabs li,.product-card__review-link a,.schedule-btn a").click(function () {
  $(".tab-content").hide();
  var activeTab = $(this).attr("rel");
  $("#" + activeTab).fadeIn();
  $("ul.tabs li").removeClass("active");
  $(this).addClass("active");
  $(".tab_drawer_heading").removeClass("d_active");
  $(".tab_drawer_heading[rel^='" + activeTab + "']").addClass("d_active");
});
/* if in drawer mode */

$(".tab_drawer_heading").click(function () {
  var d_activeTab = $(this).attr("rel"),
    activeTabBlock = $("#" + d_activeTab + ":hidden"),
    $thisActive = $(this).not(".d_active");
  $(".tab-content").hide();
  activeTabBlock.fadeIn();
  $(".tab_drawer_heading").removeClass("d_active");
  $thisActive.addClass("d_active");
  $("ul.tabs li").removeClass("active");
  $("ul.tabs li[rel^='" + d_activeTab + "']").addClass("active");
});
/* Extra class "tab_last"
 to add border to right side
 of last tab */

$("ul.tabs li").last().addClass("tab_last");
jQuery(document).ready(function () {
  jQuery(".schedule-btn a").click(function () {
    jQuery(".schedule-link").toggleClass("active");
  });
});
jQuery(document).ready(function () {
  jQuery(".product-card__review-link a").click(function () {
    jQuery(".review-tab-link").toggleClass("active");
  });
}); //slideshow

$(document).ready(() => {
  let touchstartX = 0;
  let touchendX = 0;

  $(".product-card-slideshow__sector").on("mousemove", (event) => {
    const target = $(event.currentTarget);
    const id = target.attr("data-sector");
    const parent = target.parent().parent();
    parent.find(".product-card-slideshow__image_active").removeClass("product-card-slideshow__image_active");
    parent.find(".product-card-slideshow__dot_active").removeClass("product-card-slideshow__dot_active");
    parent.find(`[data-sector-image="${id}"]`).addClass("product-card-slideshow__image_active");
    parent.find(`[data-sector-dot="${id}"]`).addClass("product-card-slideshow__dot_active");
  });

  $(".product-card-slideshow__sectors").on("touchstart", (event) => {
    touchstartX = event.changedTouches[0].screenX;
  });

  $(".product-card-slideshow__sectors").on("touchend", (event) => {
    touchendX = event.changedTouches[0].screenX;
    const parent = $(event.currentTarget).parent();
    const img = parent.find(".product-card-slideshow__image_active");
    const id = Number(img.attr("data-sector-image"));
    const length = parent.find(".product-card-slideshow__image").length;

    if (touchendX < touchstartX) {
      parent.find(".product-card-slideshow__image_active").removeClass("product-card-slideshow__image_active");
      parent.find(".product-card-slideshow__dot_active").removeClass("product-card-slideshow__dot_active");
      if (id >= length) {
        parent.find(`[data-sector-image]:nth-child(1)`).addClass("product-card-slideshow__image_active");
        parent.find(`[data-sector-dot]:nth-child(1)`).addClass("product-card-slideshow__dot_active");
        return;
      }
      parent.find(`[data-sector-image="${id}"]`).next().addClass("product-card-slideshow__image_active");
      parent.find(`[data-sector-dot="${id}"]`).next().addClass("product-card-slideshow__dot_active");
    }
    if (touchendX > touchstartX) {
      parent.find(".product-card-slideshow__image_active").removeClass("product-card-slideshow__image_active");
      parent.find(".product-card-slideshow__dot_active").removeClass("product-card-slideshow__dot_active");
      if (id <= 1) {
        parent.find(`[data-sector-image]:nth-child(${length})`).addClass("product-card-slideshow__image_active");
        parent.find(`[data-sector-dot]:nth-child(${length})`).addClass("product-card-slideshow__dot_active");
        return;
      }
      parent.find(`[data-sector-image="${id}"]`).prev().addClass("product-card-slideshow__image_active");
      parent.find(`[data-sector-dot="${id}"]`).prev().addClass("product-card-slideshow__dot_active");
    }
  });

  $(".product-card-slideshow .product-card-slideshow__image:first-child").addClass(
    "product-card-slideshow__image_active"
  );
  $(".product-card-slideshow .product-card-slideshow__dot:first-child").addClass("product-card-slideshow__dot_active");
});

$(document).ready(function () {
  homeBanner();
  header();
  gallery();
  landing_sliders();
  up();
  chatBlock();
  toggle(); //interaction
});

function landing_sliders() {
  var $sliders = $(".landing-slider .owl-carousel");

  if ($sliders.length) {
    $sliders.each(function () {
      var $this = $(this);
      var count1, count2, count3, count4;

      if ($this.is(".landing-slider_1 .owl-carousel")) {
        count1 = 2;
        count2 = 2;
        count3 = 3;
        count4 = 4;
      } else if ($this.is(".landing-slider_2 .owl-carousel")) {
        count1 = 1;
        count2 = 2;
        count3 = 3;
        count4 = 4;
      }

      $this.owlCarousel({
        loop: true,
        margin: 20,
        responsive: {
          0: {
            items: count1,
            margin: 16,
          },
          576: {
            items: count2,
          },
          768: {
            items: count3,
          },
          992: {
            items: count4,
          },
        },
      });
    });
  }
}

function toggle() {
  var $section = $(".toggle-section"),
    speed = 250;
  $section.each(function () {
    var $this = $(this),
      $toggle = $this.children(".toggle-section__trigger"),
      $content = $this.children(".toggle-section__content"),
      $close = $content.find(".toggle-section__close"),
      state = $this.hasClass("active") ? true : false,
      initialized;
    $toggle.on("click", function () {
      state = !state ? true : false;
      check();
    });
    $close.on("click", function () {
      state = false;
      check();
    });

    if ($this.is("[data-hover]")) {
      var timeout;
      $toggle.add($content).on("mouseenter", function (event) {
        if (!isTouch) {
          if (timeout) clearTimeout(timeout);
          state = true;
          check();
        }
      });
      $toggle.add($content).on("mouseleave", function (event) {
        if (!isTouch) {
          var delay;

          if ($(this).is($toggle)) {
            delay = 500;
          } else {
            delay = 100;
          }

          timeout = setTimeout(function () {
            state = false;
            check();
          }, delay);
        }
      });
    }

    if ($this.is("[data-out-hide]") || $this.is("[data-hover]")) {
      $(document).on("click touchstart", function (event) {
        var $target = $(event.target);

        if (!$target.closest($content).length && !$target.closest($toggle).length && state) {
          state = false;
          check();
        }
      });
    }

    function check() {
      if (state) {
        $this.add($content).add($toggle).addClass("active");

        if ($this.is("[data-slide]")) {
          $content.slideDown(speed);
        }
      } else {
        $this.add($toggle).add($content).removeClass("active");

        if ($this.is("[data-slide]")) {
          if (initialized) {
            $content.stop().slideUp(speed);
          } else {
            $content.hide(0);
          }
        }
      }
    }

    check();
    initialized = true;
  });
}

function up() {
  var $btn = $(".js-up");

  function check() {
    var scroll = $(window).scrollTop();

    if (scroll > 50) {
      $btn.addClass("visible");
    } else {
      $btn.removeClass("visible");
    }
  }

  let isThrottled = false;
  $(window).on("scroll", function () {
    if (isThrottled) return;
    isThrottled = true;
    setTimeout(() => {
      check();
      isThrottled = false;
    }, 100);
  });
  check();
  $btn.on("click", function (event) {
    event.preventDefault();
    $("html, body").animate(
      {
        scrollTop: 0,
      },
      500
    );
  });
}

function chatBlock() {
  var $block = $(".chat-block"),
    $open = $("[data-chat-open]"),
    $close = $("[data-chat-close]");
  $open.on("click", function () {
    $block.addClass("active");
  });
  $close.on("click", function () {
    $block.removeClass("active");
  });
}

// header-custom.js

$(document).ready(() => {
  const srcMenu = $("#menu");
  const srcNavbar = $("#menu-navbar");
  if (!srcMenu.length || !srcNavbar.length) return;

  const menu = new Mmenu("#menu", {
    offCanvas: {
      position: srcMenu.attr("data-position"),
    },
    navbars: [
      {
        content: srcNavbar.html(),
      },
    ],
    screenReader: {
      closeMenu: "Close menu",
    },
    page: {
      noSelector: [],
    },
    hooks: {
      "initMenu:before": () => {
        srcNavbar.remove();
      },
    },
  });

  const menuApi = menu.API;

  $("[data-open-menu]").on("click", () => {
    menuApi.openPanel();
  });

  $("[data-close-menu]").on("click", () => {
    menuApi.close();
  });

  // legacy buttons support
  $("#my-button").on("click", () => {
    menuApi.open();
  });
});

$(document).ready(() => {
  // phone toggle
  document.addEventListener("click", function (e) {
    if (!e.target.matches(".contact-box p")) return;
    else {
      e.target.classList.add("toggled");
    }
  });

  // catalog and menu vars
  var catalogBtn = document.querySelector(".catalog-btn");
  var catalogBox = document.querySelector(".catalog-box");
  var menuBtn = document.querySelector(".menu-btn");
  var menuBox = document.querySelector(".menu-box");

  // catalog open
  document.addEventListener("click", function (e) {
    if (e.target.matches(".catalog-btn")) {
      catalogBtn.classList.toggle("toggled");
      catalogBox.classList.toggle("show");
      if (menuBtn) {
        menuBtn.classList.remove("toggled");
        menuBox.classList.remove("show");
      }
    } else {
      return;
    }
  });

  // menu open
  document.addEventListener("click", function (e) {
    if (e.target.matches(".menu-btn")) {
      menuBtn.classList.toggle("toggled");
      menuBox.classList.toggle("show");
      if (catalogBtn) {
        catalogBtn.classList.remove("toggled");
        catalogBox.classList.remove("show");
      }
    } else {
      return;
    }
  });
});

// scripts-desktop.js

$(() => {
  if (window.innerWidth >= 767) {
    $(".product-slider--5 .owl-carousel").owlCarousel({
      loop: true,
      margin: 11,
      nav: true,
      dots: false,
      responsive: {
        0: {
          items: 1,
        },
        768: {
          items: 3,
        },
        992: {
          items: 4,
        },
      },
    });
    $(".product-slider--4:not(.product-slider--5) .owl-carousel").owlCarousel({
      loop: true,
      margin: 11,
      nav: true,
      dots: false,
      items: 5,
      responsive: {
        0: {
          items: 1,
        },
        768: {
          items: 3,
        },
        992: {
          items: 4,
        },
        1240: {
          items: 5,
        },
      },
    });
    $(".product-slider--3 .owl-carousel").owlCarousel({
      loop: true,
      margin: 11,
      nav: true,
      dots: false,
      responsive: {
        0: {
          items: 1,
        },
        768: {
          items: 2,
        },
        992: {
          items: 3,
        },
        1240: {
          items: 4,
        },
      },
    });

    function goTo(selector) {
      var lastVisible = document.querySelector(selector);

      if (lastVisible) {
        var elemRect = lastVisible.getBoundingClientRect();
        var bodyRect = document.body.getBoundingClientRect();
        var offset = elemRect.bottom - bodyRect.top;
        window.scrollTo(0, offset);
      }
    }
  } else {
    ("use strict");

    function goTo(selector) {
      var lastVisible = document.querySelector(selector);

      if (lastVisible) {
        var elemRect = lastVisible.getBoundingClientRect();
        var bodyRect = document.body.getBoundingClientRect();
        var offset = elemRect.bottom - bodyRect.top;
        window.scrollTo(0, offset);
      }
    }

    $(function () {
      $(".product-slider--3 .item").slice(0, 2).show();
      $(".btn-download-1").on("click", function (e) {
        e.preventDefault();
        $(".product-slider--3 .item:hidden").slice(0, 2).show();
        goTo(".product-slider--3 .item:nth-child(2)");

        if ($(".product-slider--3 .item:hidden").length == 0) {
          $("#load").show();
        }
      });
    });
    $(function () {
      $(".actions-content .item").slice(0, 4).show();
      $(".btn-download-4").on("click", function (e) {
        e.preventDefault();
        $(".actions-content .item:hidden").slice(0, 3).show();
        goTo(".actions-content .item:nth-child(3)");

        if ($(".actions-content .item:hidden").length == 0) {
          $("#load").show();
        }
      });
    });
    $(function () {
      $(".articles-block .item").slice(0, 4).show();
      $(".btn-download-5").on("click", function (e) {
        e.preventDefault();
        $(".articles-block .item:hidden").slice(0, 3).show();
        goTo(".articles-block .item:nth-child(5)");

        if ($(".articles-block .item:hidden").length == 0) {
          $("#load").show();
        }
      });
    });
    $(function () {
      $(".catalog-menu--search .catalog-menu-item").slice(0, 4).show();
      $(".btn-download-6").on("click", function (e) {
        e.preventDefault();
        $(".catalog-menu--search .catalog-menu-item:hidden").slice(0, 2).show();
        goTo(".catalog-menu--search .catalog-menu-item:nth-child(4)");

        if ($(".catalog-menu--search .catalog-menu-item:hidden").length == 0) {
          $("#load").show();
        }
      });
    });
    $(function () {
      $(".catalog-content--search-results .product-item").slice(0, 4).show();
      $(".btn-download-7").on("click", function (e) {
        e.preventDefault();
        $(".catalog-content--search-results .product-item:hidden").slice(0, 2).show();
        goTo(".catalog-content--search-results .product-item:nth-child(4)");

        if ($(".catalog-content--search-results .product-item:hidden").length == 0) {
          $("#load").show();
        }
      });
    });
    $(function () {
      $(".catalog-content .product-item").slice(0, 4).show();
      $(".btn-download-8").on("click", function (e) {
        e.preventDefault();
        $(".catalog-content .product-item:hidden").slice(0, 4).show();
        goTo(".catalog-content .product-item:nth-child(4)");

        if ($(".catalog-content .product-item:hidden").length == 0) {
          $("#load").show();
        }
      });
    });
    $(".city-selection__link").click(function () {
      $(".city-selection__list").toggle(0);
    });
    var $banners = $(".product-slider__banners.owl-carousel, .new-banners.owl-carousel");
    $banners.each(function () {
      console.log($(this));
      var $this = $(this); //

      if ($this.find(".item").length > 2) {
        $this.owlCarousel({
          loop: true,
          nav: false,
          dots: true,
          items: 2,
          responsive: {
            0: {
              nav: false,
              dots: true,
            },
            768: {
              nav: false,
              dots: false,
            },
          },
        });
      }
    }); //$(function () {
    //  $(".product-slider--third .item").slice(0, 2).show();
    //  $(".btn-download-1").on('click', function (e) {
    //    e.preventDefault();
    //    $(".product-slider--third .item:hidden").slice(0, 2).show();
    //    if ($(".product-slider--third .item:hidden").length == 0) {
    //      $("#load").show();
    //    }
    //  });
    //});
    //

    $(function () {
      $(".product-slider--4 .item").slice(0, 4).show();
      $(".btn-download-2").on("click", function (e) {
        e.preventDefault();
        $(".product-slider--4 .item:hidden").slice(0, 4).show();
        goTo(".product-slider--4 .item:nth-child(4)");

        if ($(".product-slider--4 .item:hidden").length == 0) {
          $("#load").show();
        }
      });
    });
    $(".actions-content .owl-carousel").owlCarousel({
      loop: true,
      margin: 20,
      nav: true,
      dots: false,
      items: 3,
      responsive: {
        0: {
          nav: false,
          dots: true,
          items: 1,
        },
        479: {
          nav: false,
          dots: true,
          items: 2,
        },
      },
    });
    $(".articles-block .owl-carousel").owlCarousel({
      loop: true,
      margin: 10,
      nav: true,
      dots: false,
      items: 3,
      responsive: {
        0: {
          nav: false,
          dots: true,
          items: 1,
        },
        479: {
          nav: false,
          dots: true,
          items: 2,
        },
      },
    });

    function moveBtnexitToLktop() {
      if (!document.querySelector(".page-head > .btn-exit")) {
        var btnexitBlock = document.querySelector(".btn-exit");
        var lktopBlock = document.querySelector(".page-head");

        if (lktopBlock && btnexitBlock) {
          lktopBlock.appendChild(btnexitBlock);
        }
      }
    }

    function moveCompareToHeadright() {
      if (!document.querySelector(".top-header__content-right > .header-compare")) {
        var compareBlock = document.querySelector(".header-compare");
        var headrightBlock = document.querySelector(".top-header__content-right");

        if (headrightBlock && compareBlock) {
          headrightBlock.appendChild(compareBlock);
        }
      }
    }

    function moveCartToHeadright() {
      if (!document.querySelector(".top-header__content-right > .header-cart")) {
        var cartBlock = document.querySelector(".header-cart");
        var headrightBlock = document.querySelector(".top-header__content-right");

        if (headrightBlock && cartBlock) {
          headrightBlock.appendChild(cartBlock);
        }
      }
    }

    function moveBtnToMobbtn() {
      if (!document.querySelector(".mobile-btn-container > .btn-form")) {
        var btnBlock = document.querySelector(".btn-form");
        var mobbtnBlock = document.querySelector(".mobile-btn-container");

        if (mobbtnBlock && btnBlock) {
          mobbtnBlock.appendChild(btnBlock);
        }
      }
    }

    function handleResize() {
      var width = window.innerWidth;

      if (width < 768) {
        moveBtnexitToLktop();
        moveCompareToHeadright();
        moveCartToHeadright();
        moveBtnToMobbtn();
        return;
      }
    }

    window.addEventListener("resize", handleResize);
    handleResize();
  }
});

// common.js

$(document).ready(function () {
  if (window.innerWidth < 767) {
    $(".product-item.product-item--wide").removeClass("product-item--wide");
  }
  var sysMessages = $("#system-messages");
  if (sysMessages) {
    $.fancybox.open(sysMessages);
  }
  // phone mask init
  $('.phone:not(".skip-mask")').inputmask("+9 (999) 999-99-99", {
    placeholder: "",
    showMaskOnHover: false,
  });
  $('.phone:not(".skip-mask")').on("input", function () {
    const value = $(this).val();
    if (value[1] == 8) {
      $(this).val(7 + value.slice(2));
      return;
    }
    if (value[1] != 8 && value[1] != 7 && value[1]) {
      $(this).val("7" + value);
      return;
    }
  });

  headerPhones();
});

function externalLinksInit() {
  var links = document.getElementsByTagName("a");
  for (var i = 0; i < links.length; i++) {
    if (links[i].href.startsWith("http") && linkIsExternal(links[i])) {
      links[i].setAttribute("target", "_blank");
    }
  }
}

function linkIsExternal(link_element) {
  return link_element.host !== window.location.host;
}

function headerPhones() {
  let phoneToggle = document.querySelector(".header-phones__toggle");
  if (phoneToggle) {
    phoneToggle.addEventListener("click", function () {
      $(".header-phones.top-header__phones .header-phones__inner").show();
    });
  }
}

// frontpage.js

$(document).ready(function () {
  $(".category-slider .owl-carousel").owlCarousel({
    loop: true,
    margin: 20,
    nav: true,
    items: 5,
    responsive: {
      0: {
        nav: false,
        dots: true,
        items: 1,
      },
      479: {
        nav: false,
        dots: true,
        items: 3,
      },
      768: {
        nav: true,
        dots: false,
        items: 4,
      },
      992: {
        nav: true,
        items: 5,
      },
    },
  });
});

$(() => {
  $(".tabs-slider-mobile").slick({
    infinite: !1,
    slidesToShow: 2.5,
    slidesToScroll: 1,
    arrows: !1,
    variableWidth: !1,
    centerMode: !1,
  });
});
