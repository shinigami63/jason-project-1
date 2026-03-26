document.addEventListener('DOMContentLoaded', async () => {
  const sendBtn = document.getElementById('sendBtn');
  const message = document.getElementById('message');
  const serverStatus = document.getElementById('serverStatus');
  const pageStatus = document.getElementById('pageStatus');

  let isToters = false;
  let serverRunning = false;

  // Check current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  isToters = tab.url && tab.url.includes('totersapp.com');

  if (isToters) {
    pageStatus.classList.add('ok');
  } else {
    pageStatus.classList.add('err');
  }

  // Check server status
  chrome.runtime.sendMessage({ action: 'checkServer' }, (res) => {
    serverRunning = res && res.running;
    if (serverRunning) {
      serverStatus.classList.add('ok');
    } else {
      serverStatus.classList.add('err');
    }
    updateButton();
  });

  function updateButton() {
    sendBtn.disabled = !(isToters && serverRunning);
  }

  sendBtn.addEventListener('click', () => {
    if (!isToters || !serverRunning) return;

    sendBtn.disabled = true;
    sendBtn.classList.add('loading');
    sendBtn.textContent = 'Sending...';
    message.className = 'message';
    message.textContent = '';

    chrome.tabs.sendMessage(tab.id, { action: 'extractPageText' }, (response) => {
      if (chrome.runtime.lastError || !response || !response.text) {
        showError('Could not extract page content. Try refreshing the Toters page.');
        resetButton();
        return;
      }

      chrome.runtime.sendMessage({ action: 'sendToFlask', text: response.text }, (result) => {
        resetButton();
        if (result && result.success) {
          const count = result.data.items ? result.data.items.length : 0;
          showSuccess('Order sent! ' + count + ' item(s) found.');
        } else {
          showError(result ? result.error : 'Unknown error');
        }
      });
    });
  });

  function showSuccess(text) {
    message.className = 'message success';
    message.textContent = text;
  }

  function showError(text) {
    message.className = 'message error';
    message.textContent = text;
  }

  function resetButton() {
    sendBtn.disabled = false;
    sendBtn.classList.remove('loading');
    sendBtn.textContent = 'Send to Kebbet Zamen';
  }
});
