const test = require("node:test");
const assert = require("node:assert/strict");

require("../chrome-extension/routing.js");
const { completionDelay, shouldPreserveArmedState } = globalThis.CameraNotifierRouting;

test("fires immediately when ChatGPT renders the response action", () => {
  assert.equal(completionDelay(true), 0);
});

test("uses a short fallback settle delay without the response action", () => {
  assert.equal(completionDelay(false), 250);
});

test("preserves a recent new-chat transition", () => {
  assert.equal(shouldPreserveArmedState("https://chatgpt.com/", "https://chatgpt.com/c/123", 10_000, 12_000), true);
});

test("preserves a GPT landing-page transition", () => {
  assert.equal(shouldPreserveArmedState("https://chatgpt.com/g/g-demo", "https://chatgpt.com/c/123", 10_000, 12_000), true);
});

test("does not preserve ordinary conversation navigation", () => {
  assert.equal(shouldPreserveArmedState("https://chatgpt.com/c/old", "https://chatgpt.com/c/new", 10_000, 12_000), false);
});

test("does not preserve stale or cross-origin transitions", () => {
  assert.equal(shouldPreserveArmedState("https://chatgpt.com/", "https://chatgpt.com/c/123", 10_000, 40_001), false);
  assert.equal(shouldPreserveArmedState("https://example.com/", "https://chatgpt.com/c/123", 10_000, 12_000), false);
});
