(function ($) {
  $(document).ready(function () {
    $(".input-number").each(function () {
      let spinner = $(this),
        input = spinner.find('input[type="number"]'),
        btnUp = spinner.find(".order-up"),
        btnDown = spinner.find(".order-down"),
        min = parseInt(input.attr("min")),
        max = input.attr("max"),
        multiplicity = parseInt(input.attr("step")),
        qty;

      if (max === "inf") {
        max = Infinity;
      } else {
        max = parseInt(max);
      }
      btnUp.click(function () {
        qty = parseInt(input.val());
        if (qty > max) {
          input.val(max);
        } else if (qty < max) {
          input.val(qty + multiplicity);
        }
        input.trigger("change");
      });
      input.change(function () {
        qty = parseInt(input.val());
        if (qty > 9 && qty <= 99) {
          btnDown.css("right", 57);
        } else if (qty > 99 && qty <= 999) {
          btnDown.css("right", 74);
        } else if (qty > 999) {
          btnDown.css("right", 90);
        } else {
          btnDown.css("right", 45);
        }
      });
      btnDown.click(function () {
        qty = parseInt(input.val());
        if (qty < min) {
          input.val(min);
        } else if (qty > min) {
          input.val(qty - multiplicity);
        }

        input.trigger("change");
      });
    });

    // добавление товара в корзину
    // ссылка обновления кол-ва товара должна иметь класс add-to-cart
    $(document).on("click", ".add-to-cart", function (e) {
      e.preventDefault();

      // Элемент, на который меняется кнопка добавления в корзину
      // после нажатия и успешного добавления.
      const CHECKOUT_BTN = `<a href="/cart/"
                                     class="st-button st-button_primary w-100">Оформить</a>`;

      var $this = $(this),
        qty = $("input", $this.prev()).val(),
        url = $this.attr("href");

      if (typeof qty !== "undefined") {
        url += "?qty=" + qty;
      }

      $.getJSON(url, function (response) {
        $this.prev().not(".input-number--lg").hide();
        $this.replaceWith(CHECKOUT_BTN);
        if (response.result == "success") {
          if (window.location.pathname == URLS.cart) {
            window.location.reload(true);
          } else {
            var count = response.count;
            $(".cart-number").html(count);
            $(".header-8march__cart-count").html(count);
            var $badge = $(".mobile-bottom-nav-8march__badge");
            if ($badge.length) {
              $badge.text(count);
            } else if (count && count !== "0") {
              $(".mobile-bottom-nav-8march__icon--cart").append('<span class="mobile-bottom-nav-8march__badge">' + count + '</span>');
            }
          }
        }
      });
    });

    // обновление кол-ва товара
    // ссылка обновления кол-ва товара должна иметь класс cart-qty-control
    $(".cart-qty-control").click(function (e) {
      var $this = $(this);
      updateQtyAjax($this, $this.data("qty-update-url"));
    });

    // обновление кол-ва товара при вводе в поле
    $(".cart-qty-control-input").on("input", function (e) {
      var $this = $(this),
        updateUrl = $this.data("qty-update-url") + "?qty=" + $this.val();
      updateQtyAjax($this, updateUrl);
    });

    function updateQtyAjax(element, url) {
      $.getJSON(url, function (response) {
        element.notify(response.message, response.result);
        if (response.result == "success") {
          element
          .closest("span")
          .next()
          .html(response.product_price_total + ' <span class="rouble"> ₽</span>');
          $(".cart-total-price").html(response.total_price + " ₽");
          $(".cart-total-weight").html(response.total_weight);
          $(".cart-total-volume").html(response.total_volume);
          $(element).parent().find("input.cart-qty-control-input").val(response.quantity);
          var count = response.count;
          if (typeof count !== "undefined") {
            $(".cart-number").html(count);
            $(".header-8march__cart-count").html(count);
            var $badge = $(".mobile-bottom-nav-8march__badge");
            if ($badge.length) {
              $badge.text(count);
            } else if (count && count !== "0") {
              $(".mobile-bottom-nav-8march__icon--cart").append('<span class="mobile-bottom-nav-8march__badge">' + count + '</span>');
            } else {
              $(".mobile-bottom-nav-8march__badge").remove();
            }
          }
        }
      });
    }

    $(".shopping-cart-item__delete").click(function (e) {
      var url = $(this).data("cart-delete-url");
      if (url) {
        window.location = url;
      }
    });

    showLoginFormCheckbox();
  });
})(jQuery);

function showLoginFormCheckbox() {
  $("#account-exists-checkbox").click(function () {
    var loginForm = $("#commerce-login-form");
    if (this.checked) {
      loginForm.show();
    } else {
      loginForm.hide();
    }
  });
}