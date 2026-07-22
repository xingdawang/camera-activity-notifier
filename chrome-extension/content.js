(() => {
  const S = globalThis.ChatGPTSelectors;
  let state = { armed: false, generating: false, sentAt: 0, lastChange: 0, round: 0, fired: false, route: location.href };
  const any = selectors => selectors.some(s => document.querySelector(s));
  const text = () => { const nodes = S.assistantMessages.flatMap(s => [...document.querySelectorAll(s)]); return nodes.at(-1)?.innerText || ""; };
  let previousText = text();
  let settleTimer;
  function arm() { state = { ...state, armed: true, generating: false, sentAt: Date.now(), lastChange: Date.now(), round: state.round + 1, fired: false, route: location.href }; previousText = text(); }
  function isRegenerate(button) {
    const label = [button.textContent, button.getAttribute("aria-label"), button.getAttribute("title")].filter(Boolean).join(" ").toLocaleLowerCase();
    return S.regenerateButton.some(selector => button.matches(selector)) || S.regenerateLabels.some(word => label.includes(word));
  }
  function userAction(event) {
    // ChatGPT may put Retry/Regenerate in a Radix menu item rather than a button.
    const target = event.target.closest("button, [role='menuitem'], [data-testid]");
    if (target && (S.sendButton.some(s => target.matches(s)) || isRegenerate(target))) arm();
  }
  document.addEventListener("click", userAction, true);
  document.addEventListener("keydown", event => { if (event.key === "Enter" && !event.shiftKey && any(S.composer)) setTimeout(arm, 0); }, true);
  new MutationObserver(() => {
    if (location.href !== state.route) { state = { ...state, armed: false, route: location.href, fired: false }; previousText = text(); return; }
    if (!state.armed || state.fired) return;
    const now = Date.now(), current = text(), stopVisible = any(S.stopButton);
    if (current !== previousText) { previousText = current; state.lastChange = now; state.generating = true; }
    if (stopVisible) state.generating = true;
    // Need observed generation, no stop button, and a stable final assistant message.
    clearTimeout(settleTimer);
    if (state.generating && !stopVisible && current) settleTimer = setTimeout(() => {
      if (!state.fired && state.armed && !any(S.stopButton) && text() === previousText) {
        state.fired = true;
        chrome.runtime.sendMessage({ type: "response-completed", conversationUrl: location.href, roundId: `${state.sentAt}-${state.round}`, isBackground: document.visibilityState !== "visible" });
      }
    }, 1550);
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
})();
