// Keep all site-specific heuristics here. They intentionally use roles, labels,
// and semantic attributes before implementation-specific selectors.
globalThis.ChatGPTSelectors = {
  composer: ["textarea", "[contenteditable='true'][role='textbox']", "form textarea"],
  sendButton: ["button[data-testid='send-button']", "button[aria-label*='Send']", "button[type='submit']"],
  regenerateButton: ["[data-testid*='regenerate']", "[data-testid*='retry']", "button[aria-label*='Regenerate']", "button[aria-label*='重新生成']", "button[aria-label*='Try again']", "[role='menuitem'][aria-label*='Regenerate']", "[title*='Regenerate']", "[title*='重新生成']"],
  regenerateLabels: ["regenerate", "retry", "try again", "重新生成", "重新回答", "再试一次"],
  stopButton: ["button[data-testid='stop-button']", "button[aria-label*='Stop generating']", "button[aria-label*='Stop streaming']"],
  assistantMessages: ["[data-message-author-role='assistant']", "article [data-message-author-role='assistant']", "main [role='article']"]
};
