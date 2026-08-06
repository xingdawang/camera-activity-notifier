(() => {
  const S = globalThis.ChatGPTSelectors;
  const R = globalThis.CameraNotifierRouting;
  let state = { armed: false, generating: false, sentAt: 0, lastChange: 0, round: 0, fired: false, route: location.href };
  const any = selectors => selectors.some(s => document.querySelector(s));
  const lastAssistant = () => [...document.querySelectorAll(S.assistantMessages.join(","))].at(-1);
  const text = () => lastAssistant()?.innerText || "";
  const responseComplete = () => {
    const turn = lastAssistant()?.closest("[data-testid^='conversation-turn-']");
    return Boolean(turn && S.responseComplete.some(selector => turn.querySelector(selector)));
  };
  let previousText = text();
  let settleTimer;
  function fire() {
    if (state.fired || !state.armed || any(S.stopButton)) return;
    state.fired = true;
    chrome.runtime.sendMessage({ type: "response-completed", conversationUrl: location.href, roundId: `${state.sentAt}-${state.round}`, isBackground: document.visibilityState !== "visible" });
  }
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
    if (location.href !== state.route) {
      const preserve = state.armed && R.shouldPreserveArmedState(state.route, location.href, state.sentAt);
      state = { ...state, armed: preserve, route: location.href, fired: false };
      if (!preserve) { previousText = text(); return; }
    }
    if (!state.armed || state.fired) return;
    const now = Date.now(), current = text(), stopVisible = any(S.stopButton);
    if (current !== previousText) { previousText = current; state.lastChange = now; state.generating = true; }
    if (stopVisible) state.generating = true;
    // The response action appears only after the current turn finishes, so it
    // is a stronger and faster completion signal than a long text-settle wait.
    clearTimeout(settleTimer);
    if (state.generating && !stopVisible && current) {
      const delay = R.completionDelay(responseComplete());
      if (delay === 0) fire();
      else settleTimer = setTimeout(() => { if (text() === previousText) fire(); }, delay);
    }
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
})();
