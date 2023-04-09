window.onload = function () {
  removeTempMessagesAfterTimeout();
  setOnChangeToSubmitInPeriodFormSelects();
}

function removeTempMessagesAfterTimeout() {
  const SHORT_TIME_MESSAGES = 5
  const MID_TIME_MESSAGES = 10
  const LONG_TIME_MESSAGES = 30
  setTimeout(
    () => document.querySelectorAll(".short-time-msg").forEach((e) => e.remove()),
    SHORT_TIME_MESSAGES * 1000
  )
  setTimeout(
    () => document.querySelectorAll(".mid-time-msg").forEach((e) => e.remove()),
    MID_TIME_MESSAGES * 1000
  )
  setTimeout(
    () => document.querySelectorAll(".long-time-msg").forEach((e) => e.remove()),
    LONG_TIME_MESSAGES * 1000
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
