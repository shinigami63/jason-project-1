// Content script injected on Toters order pages
// Extracts page text when requested by the popup/background

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'extractPageText') {
    sendResponse({ text: document.body.innerText });
  }
  if (message.action === 'ping') {
    sendResponse({ onTotersPage: true });
  }
  return true;
});
