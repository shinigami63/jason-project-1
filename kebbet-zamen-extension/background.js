const FLASK_URL = 'http://127.0.0.1:5001';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'sendToFlask') {
    fetch(`${FLASK_URL}/extension/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: message.text })
    })
    .then(async (res) => {
      const data = await res.json();
      if (res.ok) {
        sendResponse({ success: true, data: data });
      } else {
        sendResponse({ success: false, error: data.error || 'Parse failed' });
      }
    })
    .catch(() => {
      sendResponse({
        success: false,
        error: 'Cannot reach Kebbet Zamen app. Is it running?'
      });
    });
    return true;
  }

  if (message.action === 'checkServer') {
    fetch(`${FLASK_URL}/`, { method: 'HEAD' })
      .then(() => sendResponse({ running: true }))
      .catch(() => sendResponse({ running: false }));
    return true;
  }
});
