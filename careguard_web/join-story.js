/* Local-only story controls. No requests, storage, submissions, or fabricated results. */
(() => {
  "use strict";
  const root = document.getElementById("join-view");
  if (!root) return;
  const tabs = [...root.querySelectorAll("[data-join-case]")];
  const panels = [...root.querySelectorAll(".join-case-panel")];
  function selectCaseTab(selected, focus = false) {
    tabs.forEach(tab => {
      const active = tab === selected;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    panels.forEach(panel => { panel.hidden = panel.id !== selected.getAttribute("aria-controls"); });
    if (focus) selected.focus();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectCaseTab(tab));
    tab.addEventListener("keydown", event => {
      let next;
      if (["ArrowDown", "ArrowRight"].includes(event.key)) next = (index + 1) % tabs.length;
      if (["ArrowUp", "ArrowLeft"].includes(event.key)) next = (index + tabs.length - 1) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next === undefined) return;
      event.preventDefault();
      selectCaseTab(tabs[next], true);
    });
  });
  const select = document.getElementById("join-track");
  const form = document.getElementById("join-form-section");
  root.querySelectorAll("[data-join-track]").forEach(button => {
    button.addEventListener("click", () => {
      if (!select || !form) return;
      const track = button.dataset.joinTrack;
      if (![...select.options].some(option => option.value === track)) return;
      select.value = track;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      form.scrollIntoView({ block: "start", behavior: "instant" });
      select.focus({ preventScroll: true });
    });
  });
})();
