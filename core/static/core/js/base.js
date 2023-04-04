window.onload = function () {
  removeTempMessagesAfterTimeout();
  setOnChangeToSubmitInPeriodFormSelects();
}

function removeTempMessagesAfterTimeout() {
  const TIME_TO_REMOVE_TEMP_MESSAGES = 5
  setTimeout(
    () => document.querySelectorAll(".temp-msg").forEach((e) => e.remove()),
    TIME_TO_REMOVE_TEMP_MESSAGES * 1000
  )
}

function setOnChangeToSubmitInPeriodFormSelects() {
  const selects = document.querySelectorAll(".period-form");
  selects.forEach(e => e.addEventListener("change", (e) => e.target.form.submit()));
}

function expandDetailRow(rowId) {
  const expandIcon = document.querySelector(
    `[name='clickable-row${rowId}'] td:last-child`
  )
  expandIcon.innerHTML = expandIcon.innerHTML === "Palpites 🔽" ?
    "Palpites 🔼" : "Palpites 🔽"

  const row = document.querySelector(`[name='detail-row${rowId}']`)
  row.style.display = row.style.display === "none" ?
    "table-row" : "none"
}
