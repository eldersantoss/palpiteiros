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
