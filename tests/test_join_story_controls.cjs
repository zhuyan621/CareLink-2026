/* Unit-test the new controls with a small DOM fixture; not browser/render QA. */
"use strict";
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = readFileSync(path.join(__dirname, "../careguard_web/join-story.js"), "utf8");
class Item {
  constructor(id, attributes = {}) {
    this.id = id;
    this.attributes = attributes;
    this.handlers = {};
    this.dataset = {};
    this.hidden = false;
    this.tabIndex = -1;
  }
  getAttribute(name) { return this.attributes[name]; }
  setAttribute(name, value) { this.attributes[name] = value; }
  addEventListener(type, handler) { this.handlers[type] = handler; }
  focus() { this.focused = true; }
  dispatchEvent(event) { this.events = [...(this.events || []), event.type]; }
  scrollIntoView(options) { this.scrolled = options; }
}
const names = ["input", "compute", "source", "human", "export"];
const tabs = names.map(name => new Item(`join-case-tab-${name}`, { "aria-controls": `join-case-panel-${name}` }));
const panels = names.map(name => new Item(`join-case-panel-${name}`));
const tracks = ["产品与交互设计", "前端与创意技术", "后端与 AI 工程", "照护场景研究", "医学与合规咨询", "机构或项目合作"];
const roles = tracks.map(track => { const item = new Item(track); item.dataset.joinTrack = track; return item; });
const select = new Item("join-track");
select.options = tracks.map(value => ({ value }));
select.value = "";
const form = new Item("join-form-section");
const root = { querySelectorAll: selector => ({ "[data-join-case]": tabs, ".join-case-panel": panels, "[data-join-track]": roles })[selector] };
const document = { getElementById: id => ({ "join-view": root, "join-track": select, "join-form-section": form })[id] };
vm.runInNewContext(source, { document, Event: class { constructor(type) { this.type = type; } } });
tabs.forEach((tab, selectedIndex) => {
  tab.handlers.click();
  assert.equal(panels.filter(panel => !panel.hidden).length, 1);
  panels.forEach((panel, index) => assert.equal(panel.hidden, index !== selectedIndex));
  tabs.forEach((item, index) => {
    assert.equal(item.getAttribute("aria-selected"), String(index === selectedIndex));
    assert.equal(item.tabIndex, index === selectedIndex ? 0 : -1);
  });
});
let prevented = 0;
function key(index, name) { tabs[index].handlers.keydown({ key: name, preventDefault() { prevented++; } }); }
key(4, "ArrowDown"); assert.equal(tabs[0].tabIndex, 0); assert.equal(tabs[0].focused, true);
key(0, "ArrowUp"); assert.equal(tabs[4].tabIndex, 0);
key(4, "Home"); assert.equal(tabs[0].tabIndex, 0);
key(0, "End"); assert.equal(tabs[4].tabIndex, 0);
key(0, "ArrowRight"); assert.equal(tabs[1].tabIndex, 0);
key(1, "ArrowLeft"); assert.equal(tabs[0].tabIndex, 0);
key(0, "Tab"); assert.equal(prevented, 6);
roles.forEach((role, index) => {
  role.handlers.click();
  assert.equal(select.value, tracks[index]);
  assert.equal(select.focused, true);
  assert.equal(form.scrolled.block, "start");
});
assert.deepEqual(select.events, Array(6).fill("change"));
const before = select.value;
roles[0].dataset.joinTrack = "invalid";
roles[0].handlers.click();
assert.equal(select.value, before);
vm.runInNewContext(source, { document: { getElementById: () => null } });
console.log("PASS: 5 case panels, 6 keyboard transitions, 6 role prefills, invalid track, missing root; no network/storage APIs exposed.");
