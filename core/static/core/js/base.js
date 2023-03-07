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

function setOnChangeSubmitInPeriodFormSelects() {
  const selects = document.querySelector(".period-form").elements
  for (let i = 0; i < selects.length; i++) {
    const element = selects[i]
    element.addEventListener("change", () => element.form.submit())
  }
}

setOnChangeSubmitInPeriodFormSelects()
