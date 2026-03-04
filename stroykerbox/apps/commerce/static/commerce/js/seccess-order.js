$(() => {
  if (typeof roistat !== "undefined") {
    roistat.event.send("orderForm", {});
  }
})