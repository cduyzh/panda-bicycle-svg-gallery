/* 自定义排序选择器：当前项、键盘焦点和提交值分开管理。 */
function setupSortDropdown() {
  const choices = [
    { value: "recent", label: "最近更新", note: "先看最近更新的作品", icon: '<circle cx="10" cy="10" r="7"/><path d="M10 6v4l3 2"/>' },
    { value: "name", label: "模型名称", note: "按型号名称排列", icon: '<path d="m3 14 4-9 4 9M4.5 11h5M13 6h4l-4 8h4"/>' },
    { value: "score", label: "最新作品评分", note: "分数高的作品优先", icon: '<path d="m10 3 2 4.5 5 .5-3.8 3.3 1.2 4.7-4.4-2.5L5.6 16l1.2-4.7L3 8l5-.5Z"/>' },
  ];
  const wrap = $("sort-wrap"), trigger = $("sort"), menu = $("sort-options");
  let active = 0;
  const svg = (paths, className = "") => `<svg class="${className}" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
  const options = choices.map((choice) => {
    const option = node("button", "sort-option");
    option.type = "button";
    option.id = `sort-option-${choice.value}`;
    option.tabIndex = -1;
    option.setAttribute("role", "option");
    option.setAttribute("aria-label", choice.label);
    const icon = node("span", "sort-option-icon");
    icon.innerHTML = svg(choice.icon);
    const copy = node("span", "sort-option-copy");
    copy.append(node("strong", "", choice.label), node("small", "", choice.note));
    option.append(icon, copy);
    option.insertAdjacentHTML("beforeend", svg('<path d="m5 10 3 3 7-7"/>', "sort-check"));
    option.addEventListener("click", () => select(choice.value));
    menu.appendChild(option);
    return option;
  });
  function sync() {
    const current = choices.findIndex((choice) => choice.value === state.sort);
    $("sort-label").textContent = choices[current].label;
    trigger.setAttribute("aria-label", `排序方式：${choices[current].label}`);
    options.forEach((option, index) => {
      option.setAttribute("aria-selected", String(index === current));
      option.dataset.active = String(index === active);
    });
    menu.setAttribute("aria-activedescendant", options[active].id);
  }
  function open() {
    active = choices.findIndex((choice) => choice.value === state.sort);
    sync();
    menu.hidden = false;
    trigger.setAttribute("aria-expanded", "true");
    placeMenu();
    menu.focus({ preventScroll: true });
  }
  function placeMenu() {
    menu.style.maxHeight = "";
    const rect = trigger.getBoundingClientRect();
    const below = window.innerHeight - rect.bottom, above = rect.top;
    const upward = below < menu.offsetHeight + 16 && above > below;
    menu.dataset.placement = upward ? "top" : "bottom";
    menu.style.maxHeight = `${Math.max(80, (upward ? above : below) - 16)}px`;
    menu.style.overflowY = "auto";
  }
  function close(restoreFocus = false) {
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
    if (restoreFocus) trigger.focus({ preventScroll: true });
  }
  function select(value) {
    const changed = state.sort !== value;
    state.sort = value;
    sync();
    close(true);
    if (changed) renderGallery();
  }
  trigger.addEventListener("click", () => menu.hidden ? open() : close(true));
  trigger.addEventListener("keydown", (event) => {
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      open();
      if (event.key === "Home" || event.key === "End") {
        active = event.key === "Home" ? 0 : choices.length - 1;
        sync();
      }
    }
  });
  menu.addEventListener("keydown", (event) => {
    if (event.key === "Tab") { close(true); return; }
    if (event.key === "Escape") { event.preventDefault(); close(true); return; }
    if (["Enter", " "].includes(event.key)) {
      event.preventDefault(); select(choices[active].value); return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    if (event.key === "Home") active = 0;
    else if (event.key === "End") active = choices.length - 1;
    else active = (active + (event.key === "ArrowDown" ? 1 : -1) + choices.length) % choices.length;
    sync();
    options[active].scrollIntoView({ block: "nearest" });
  });
  document.addEventListener("pointerdown", (event) => { if (!wrap.contains(event.target)) close(); });
  wrap.addEventListener("focusout", (event) => { if (!wrap.contains(event.relatedTarget)) close(); });
  window.addEventListener("blur", () => close());
  window.addEventListener("resize", () => { if (!menu.hidden) placeMenu(); });
  sync();
}
