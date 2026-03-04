(function ($) {
  $(document).ready(function () {
    var delivery_payment_mapping = JSON.parse(document.getElementById("delivery_payment_mapping").textContent);
    var current_delivery = $("input[name=delivery_variant]:checked").val();
    var payment_block = $("#id_payment_variant").parent();

    function change_delivery_variant(e) {
      if (e) {
        current_delivery = $(this).val();
      }
      if (current_delivery) {
        payment_block.show().find("li").show();
        payment_block
        .show()
        .find("input")
        .each(function () {
          var current_element = $(this);
          if (!delivery_payment_mapping[current_delivery].includes(current_element.val())) {
            current_element.prop("checked", false).parent().parent().hide();
          }
        });
      }
    }
    $("input[name=delivery_variant]").click(change_delivery_variant);
    change_delivery_variant(undefined);
  });
})(jQuery);