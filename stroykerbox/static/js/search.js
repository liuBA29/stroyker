jQuery(document).ready(function ($) {
  let searchInputEl,
    resultBoxEl,
    mobile = false;

  if (window.innerWidth > 767) {
    searchInputEl = $(".search_input");
    resultBoxEl = $(".header-search-results");
  } else {
    searchInputEl = $(".search_input_mobile");
    resultBoxEl = $("#search-result-mob");
    mobile = true;
  }

  processSearchResult(searchInputEl, resultBoxEl, mobile);
  processSearchBtnClick(searchInputEl);
});

function processSearchResult(searchInputEl, resultBoxEl, mobile = false) {
  let searchUrl = searchInputEl.data("search-url"),
    searchMinChars = searchInputEl.data("min-chars");

  searchInputEl.on("focus keyup paste", function (e) {
    var input = $(this),
      minChars = this.dataset.minChars;
    if (input.val().length >= searchMinChars) {
      $.ajax({
        type: "get",
        url: searchUrl,
        data: input.serialize(),
        dataType: "html",
      }).done(function (result) {
        if (result.replace(/\s/g, "").length > 0) {
          resultBoxEl.html(result);
          resultBoxEl.show();
          $(document).mouseup(function (e) {
            if (!resultBoxEl.is(e.target) && resultBoxEl.has(e.target).length === 0) {
              resultBoxEl.hide();
            }
          });
        } else {
          resultBoxEl.html("");
          resultBoxEl.hide();
        }
      });
    } else {
      resultBoxEl.hide().empty();
    }
  });
}

function processSearchBtnClick(searchInputEl) {
  var searchBtn = searchInputEl.next("button");

  searchBtn.click(function () {
    var searchInputVal = searchInputEl.val();
    if (searchInputVal) {
      var url = searchInputEl.data("search-url");
      window.location = url + "?q=" + searchInputVal;
    }
  });

  searchInputEl.keyup(function (event) {
    if (event.keyCode === 13) {
      searchBtn.click();
    }
  });
}

$(document).ready(function ($) {
  $("[data-search-button]").on("click", (event) => {
    const id = $(event.currentTarget).attr("data-search-button");
    const input = $(`[data-search-input="${id}"]`);
    const value = input.val();
    const searchUrl = input.attr("data-search-url");
    window.location = searchUrl + "?q=" + value;
  });

  $("[data-search-input]").on("focus keyup paste", (event) => {
    const input = $(event.currentTarget);
    const value = input.val();
    const id = input.attr("data-search-input");
    const searchMinChars = input.attr("data-min-chars");
    const searchUrl = input.attr("data-search-url");
    const resultContainer = $(`[data-search-results="${id}"]`);
    const clickOuterHandler = (event) => {
      if (!event.target.closest("[data-search-results-active]")) {
        $(event.target).removeAttr("data-search-results-active");
        $(document).off("click", clickOuterHandler);
      }
    };

    if (event.key === "enter") return (window.location = searchUrl + "?q=" + value);

    if (value.length < searchMinChars) return;

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
          return;
        }
        resultContainer.html(result);
        resultContainer.attr("data-search-results-active", "");
        $(document).on("click", clickOuterHandler);
      });
    } catch {
      (error) => {
        console.log(error);
      };
    }
  });
});
