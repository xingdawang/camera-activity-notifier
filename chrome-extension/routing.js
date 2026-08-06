globalThis.CameraNotifierRouting = {
  completionDelay(hasResponseAction) {
    return hasResponseAction ? 0 : 250;
  },
  shouldPreserveArmedState(previousUrl, nextUrl, sentAt, now = Date.now()) {
    if (!sentAt || now - sentAt > 30_000) return false;
    try {
      const previous = new URL(previousUrl);
      const next = new URL(nextUrl);
      return previous.origin === next.origin
        && !previous.pathname.startsWith("/c/")
        && next.pathname.startsWith("/c/");
    } catch {
      return false;
    }
  }
};
