window.onload = function () {
  removeTempMessagesAfterTimeout();
};

function removeTempMessagesAfterTimeout() {
  const SHORT_TIME_MESSAGES = 5;
  const MID_TIME_MESSAGES = 10;
  const LONG_TIME_MESSAGES = 30;
  setTimeout(
    () =>
      document
        .querySelectorAll(".short-time-msg")
        .forEach((e) => e.parentElement.remove()),
    SHORT_TIME_MESSAGES * 1000
  );
  setTimeout(
    () =>
      document
        .querySelectorAll(".mid-time-msg")
        .forEach((e) => e.parentElement.remove()),
    MID_TIME_MESSAGES * 1000
  );
  setTimeout(
    () =>
      document
        .querySelectorAll(".long-time-msg")
        .forEach((e) => e.parentElement.remove()),
    LONG_TIME_MESSAGES * 1000
  );
}

function expandDetailRow(rowId) {
  const expandIcon = document.querySelector(
    `[name='clickable-row${rowId}'] td:last-child`
  );
  expandIcon.innerHTML =
    expandIcon.innerHTML === "Palpites 🔽" ? "Palpites 🔼" : "Palpites 🔽";

  const row = document.querySelector(`[name='detail-row${rowId}']`);
  row.style.display = row.style.display === "none" ? "table-row" : "none";
}

function copyUrlToClipboard(element) {
  const value = document.querySelector("#pool-url").innerHTML;
  navigator.clipboard.writeText(value);
  element.value = "Copiado ✔";
}

function showPoolLeavingConfirmation() {
  document.querySelector(".exit-confirmation").style.display = "flex";
}

function hidePoolLeavingConfirmation() {
  document.querySelector(".exit-confirmation").style.display = "none";
}
