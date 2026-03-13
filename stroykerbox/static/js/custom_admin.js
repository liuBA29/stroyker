// Admin helpers for stroykerbox.
// Keeps changes scoped and non-invasive.

(function () {
  // Превью для тегов нового дизайна: соответствие tag_line -> файл скриншота.
  // Базовый путь задаётся из шаблона админки (STATIC_URL), иначе дефолт для локальной разработки.
  var ND_TAG_PREVIEW_BASE = (typeof window.ND_TAG_PREVIEW_BASE !== "undefined" && window.ND_TAG_PREVIEW_BASE) || "/static/8march_design/images/images_admin_panel/";
  var ND_TAG_PREVIEWS = {
    "customization_tags:render_new_design_hero_block": "hero.jpg",
    "customization_tags:render_new_design_actions_block": "actions.jpg",
    "customization_tags:render_new_design_bouquets_block": "sbornye-bukety.jpg",
    "customization_tags:render_new_design_bouquet_wish_block": "your-wish-buquet.jpg",
    "customization_tags:render_new_design_categories_block": "oval.jpg",
    "customization_tags:render_new_design_collection_block": "8march_collection.jpg",
    "customization_tags:render_new_design_info_block": "waranty_delivery_rating.jpg",
    "customization_tags:render_new_design_social_block": "social.jpg",
    "customization_tags:render_new_design_reviews_block": "otzyvy.jpg",
    "customization_tags:render_new_design_map_block": "map.jpg",
    "customization_tags:render_new_design_footer_questions_block": "questions.jpg",
    "customization_tags:render_new_design_footer_menu_block": "bottom-footer.jpg",
    "customization_tags:render_new_design_footer_copyright_block": "copywright.jpg"
  };

  function isNewDesignContainerPage() {
    var keyInput = document.getElementById("id_key");
    var key = keyInput && keyInput.value;
    return typeof key === "string" && key.indexOf("new_design_") === 0;
  }

  function renumberPositions(inlineGroup) {
    var positionInputs = inlineGroup.querySelectorAll("input[name$='-position']");
    if (!positionInputs.length) return;
    // Use step 10 for easy manual inserts later.
    var pos = 0;
    positionInputs.forEach(function (inp) {
      // Skip empty template row if any
      if (inp.closest(".empty-form")) return;
      inp.value = String(pos);
      pos += 10;
    });
  }

  function moveRow(row, direction) {
    var tbody = row.parentElement;
    if (!tbody) return;
    if (direction === "up") {
      var prev = row.previousElementSibling;
      if (prev) tbody.insertBefore(row, prev);
    } else {
      var next = row.nextElementSibling;
      if (next) tbody.insertBefore(next, row);
    }
  }

  function enhanceSortableInline(inlineGroup) {
    var table = inlineGroup.querySelector("table");
    if (!table) return;
    var tbody = table.tBodies && table.tBodies[0];
    if (!tbody) return;

    // Add controls only once.
    if (inlineGroup.dataset.ndSortInit === "1") return;
    inlineGroup.dataset.ndSortInit = "1";

    // Add a header cell if possible.
    var headRow = table.tHead && table.tHead.rows && table.tHead.rows[0];
    if (headRow) {
      var th = document.createElement("th");
      th.className = "nd-sort-col";
      th.textContent = "Порядок";
      headRow.insertBefore(th, headRow.cells[0] || null);
    }

    function getTagLabelFromRow(r) {
      var sel = r.querySelector("select[name$='-tag_line']");
      if (!sel || sel.selectedIndex < 0) return "";
      var opt = sel.options[sel.selectedIndex];
      return opt ? (opt.textContent || opt.text || "").trim() : "";
    }

    function getTagValueFromRow(r) {
      var sel = r.querySelector("select[name$='-tag_line']");
      return sel ? (sel.value || "") : "";
    }

    function setPreviewTooltip(previewSpan, r) {
      previewSpan.title = getTagLabelFromRow(r) || "Выберите шаблонный тег";
    }

    function updatePreview(previewSpan, r) {
      setPreviewTooltip(previewSpan, r);
      var img = previewSpan.querySelector("img");
      if (!img) return;
      var tagValue = getTagValueFromRow(r);
      var filename = ND_TAG_PREVIEWS[tagValue];
      if (filename) {
        img.src = ND_TAG_PREVIEW_BASE + filename;
        img.style.display = "inline-block";
      } else {
        img.removeAttribute("src");
        img.style.display = "none";
      }
    }

    Array.from(tbody.rows).forEach(function (row) {
      if (row.classList.contains("empty-form")) return;
      var td = document.createElement("td");
      td.className = "nd-sort-col";

      var up = document.createElement("button");
      up.type = "button";
      up.className = "nd-sort-btn";
      up.textContent = "↑";
      up.addEventListener("click", function () {
        moveRow(row, "up");
        renumberPositions(inlineGroup);
      });

      var down = document.createElement("button");
      down.type = "button";
      down.className = "nd-sort-btn";
      down.textContent = "↓";
      down.addEventListener("click", function () {
        moveRow(row, "down");
        renumberPositions(inlineGroup);
      });

      td.appendChild(up);
      td.appendChild(down);

      var previewSpan = document.createElement("span");
      previewSpan.className = "nd-tag-preview";
      previewSpan.setAttribute("aria-label", "Подсказка: какой тег");
      var previewImg = document.createElement("img");
      previewImg.className = "nd-tag-preview-img";
      previewSpan.appendChild(previewImg);
      updatePreview(previewSpan, row);
      var sel = row.querySelector("select[name$='-tag_line']");
      if (sel) {
        sel.addEventListener("change", function () {
          updatePreview(previewSpan, row);
        });
      }
      td.appendChild(previewSpan);

      row.insertBefore(td, row.cells[0] || null);
    });

    renumberPositions(inlineGroup);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!isNewDesignContainerPage()) return;
    // Django admin inline group id/prefix can vary; find the first inline-group that contains position inputs.
    var inlineGroups = document.querySelectorAll(".inline-group");
    Array.from(inlineGroups).forEach(function (grp) {
      if (grp.querySelector("input[name$='-position']")) {
        enhanceSortableInline(grp);
      }
    });
  });
})();

