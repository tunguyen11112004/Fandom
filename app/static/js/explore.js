const form = document.querySelector(".filters");
if (form) {
  form.querySelectorAll("select").forEach((select) => {
    select.addEventListener("change", () => form.requestSubmit());
  });
}
