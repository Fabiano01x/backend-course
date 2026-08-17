document.querySelectorAll(".copy-code").forEach((button) => {
  button.addEventListener("click", async () => {
    const code = button.closest(".code-card").querySelector("code").innerText;
    await navigator.clipboard.writeText(code);
    const original = button.textContent;
    button.textContent = "Copiado";
    window.setTimeout(() => { button.textContent = original; }, 1400);
  });
});

document.querySelectorAll("table").forEach((table) => {
  const wrapper = document.createElement("div");
  wrapper.className = "table-wrap";
  table.parentNode.insertBefore(wrapper, table);
  wrapper.appendChild(table);
});
