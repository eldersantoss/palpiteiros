window.onload = function () {
  removeTempMessagesAfterTimeout();
};

function removeTempMessagesAfterTimeout() {
  const SHORT_TIME_MESSAGES = 5;
  const MID_TIME_MESSAGES = 10;
  const LONG_TIME_MESSAGES = 15;

  function removeMessagesAndCleanup(selector) {
    document.querySelectorAll(selector).forEach((e) => e.remove());
    const container = document.querySelector("ul.messages");
    if (container && container.children.length === 0) container.remove();
  }

  setTimeout(
    () => removeMessagesAndCleanup(".short-time-msg"),
    SHORT_TIME_MESSAGES * 1000,
  );
  setTimeout(
    () => removeMessagesAndCleanup(".mid-time-msg"),
    MID_TIME_MESSAGES * 1000,
  );
  setTimeout(
    () => removeMessagesAndCleanup(".long-time-msg"),
    LONG_TIME_MESSAGES * 1000,
  );
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

function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("open");
  document.getElementById("sidebar-overlay").classList.toggle("open");
}

function closeSidebar() {
  document.getElementById("sidebar").classList.remove("open");
  document.getElementById("sidebar-overlay").classList.remove("open");
}
