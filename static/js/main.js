(function () {
  var textarea = document.getElementById("description");
  var counter = document.getElementById("char-count");
  var form = document.getElementById("analyze-form");
  var button = document.getElementById("analyze-button");

  if (!textarea || !counter || !form || !button) {
    return;
  }

  var maxLength = Number(textarea.getAttribute("maxlength"));

  function updateCounter() {
    counter.textContent = textarea.value.length + " / " + maxLength;
  }

  textarea.addEventListener("input", updateCounter);
  updateCounter();

  form.addEventListener("submit", function () {
    button.disabled = true;
    button.textContent = "Analyzing...";
  });

  // Reset the button if the user comes back with the browser's Back button
  window.addEventListener("pageshow", function () {
    button.disabled = false;
    button.textContent = "Analyze Job";
  });
})();