const defaults = { port: 8765, token: "", enabled: true, onlyBackground: false };
async function settings() { return { ...defaults, ...(await chrome.storage.local.get(defaults)) }; }
async function post(path, payload) {
  const s = await settings();
  const response = await fetch(`http://127.0.0.1:${s.port}${path}`, { method: "POST", headers: { "Content-Type": "application/json", "X-Camera-Notifier-Token": s.token }, body: JSON.stringify(payload) });
  if (!response.ok) throw new Error(`Local notifier returned ${response.status}`);
  return response.json();
}
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  (async () => {
    const s = await settings();
    if (message.type === "response-completed") {
      if (!s.enabled || (s.onlyBackground && !message.isBackground)) return respond({ ok: true, skipped: true });
      const key = `completion:${message.conversationUrl}`;
      const old = await chrome.storage.session.get(key);
      if (old[key] === message.roundId) return respond({ ok: true, duplicate: true });
      await chrome.storage.session.set({ [key]: message.roundId });
      return respond(await post("/notify", { source: "chatgpt", event: "response_completed", conversation_url: message.conversationUrl, timestamp: new Date().toISOString() }));
    }
    if (message.type === "test") return respond(await post("/test", {}));
    respond({ ok: false, error: "unknown message" });
  })().catch(error => respond({ ok: false, error: error.message }));
  return true;
});
chrome.action.onClicked.addListener(() => chrome.runtime.openOptionsPage());
