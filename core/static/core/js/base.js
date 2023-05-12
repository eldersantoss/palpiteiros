window.onload = function () {
  removeTempMessagesAfterTimeout();
  setOnChangeToSubmitInPeriodFormSelects();
  // cookieConsent();
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

function setOnChangeToSubmitInPeriodFormSelects() {
  const selects = document.querySelectorAll(".period-form");
  selects.forEach((e) =>
    e.addEventListener("change", (e) => e.target.form.submit())
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

// var purecookieTitle = "Cookies.",
//   purecookieDesc =
//     "Ao usar este site, você automaticamente aceita que usemos cookies.",
//   purecookieLink =
//     '<a href="https://www.cssscript.com/privacy-policy/" target="_blank">What for?</a>',
//   purecookieButton = "Understood";

// function eraseCookie(e) {
//   document.cookie = e + "=; Max-Age=-99999999;";
// }

// function cookieConsent() {
//   getCookie("purecookieDismiss") ||
//     ((document.body.innerHTML +=
//       '<div class="cookieConsentContainer" id="cookieConsentContainer"><div class="cookieTitle"><a>' +
//       purecookieTitle +
//       '</a></div><div class="cookieDesc"><p>' +
//       purecookieDesc +
//       " " +
//       purecookieLink +
//       '</p></div><div class="cookieButton"><a onClick="purecookieDismiss();">' +
//       purecookieButton +
//       "</a></div></div>"),
//     pureFadeIn("cookieConsentContainer"));
// }

// function getCookie(e) {
//   for (
//     var o = e + "=", i = document.cookie.split(";"), t = 0;
//     t < i.length;
//     t++
//   ) {
//     for (var n = i[t]; " " == n.charAt(0); ) n = n.substring(1, n.length);
//     if (0 == n.indexOf(o)) return n.substring(o.length, n.length);
//   }
//   return null;
// }

// function pureFadeIn(e, o) {
//   var i = document.getElementById(e);
//   (i.style.opacity = 0),
//     (i.style.display = o || "block"),
//     (function e() {
//       var o = parseFloat(i.style.opacity);
//       (o += 0.02) > 1 || ((i.style.opacity = o), requestAnimationFrame(e));
//     })();
// }

// function purecookieDismiss() {
//   setCookie("purecookieDismiss", "1", 365);
//   pureFadeOut("cookieConsentContainer");
// }

// function setCookie(e, o, i) {
//   var t = "";
//   if (i) {
//     var n = new Date();
//     n.setTime(n.getTime() + 24 * i * 60 * 60 * 1e3),
//       (t = "; expires=" + n.toUTCString());
//   }
//   document.cookie = e + "=" + (o || "") + t + "; path=/";
// }

// function pureFadeOut(e) {
//   var o = document.getElementById(e);
//   (o.style.opacity = 1),
//     (function e() {
//       (o.style.opacity -= 0.02) < 0
//         ? (o.style.display = "none")
//         : requestAnimationFrame(e);
//     })();
// }
