// Admin helpers for stroykerbox.
// Keeps changes scoped and non-invasive.

(function () {
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

