window.formUtils = window.formUtils || {};

window.formUtils.applyPeriodVisibility = function (
  period,
  { anoDiv, mesDiv, semanaDiv },
) {
  if (anoDiv) {
    anoDiv.style.display = period === "anual" ? "block" : "none";
  }
  if (mesDiv) {
    mesDiv.style.display = period === "mensal" ? "block" : "none";
  }
  if (semanaDiv) {
    semanaDiv.style.display = period === "semanal" ? "block" : "none";
  }
};
