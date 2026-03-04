$("#footer-subscription-form").on("submit", function (event) {
  event.preventDefault();
  var $this = $(this),
    msg = "";
  $.post($this.attr("action"), $this.serialize(), function (data) {
    if (data.success) {
      msg = '<p style="color: white">Поздравляем! Вы успешно подписались на нашу рассылку.</p>';
      if (typeof roistat !== "undefined") {
        const obj = $this.serializeArray().reduce((acc, item) => ((acc[item.name] = item.value), acc), {});
        roistat.event.send(`newsSubForm`, obj);
      }
    } else if (data.errors) {
      for (var e in data.errors) {
        msg = msg + '<p style="color: white">' + data.errors[e] + "</p>";
      }
    }
    $this.html(msg);
  });
});
