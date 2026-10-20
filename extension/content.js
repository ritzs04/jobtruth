// Content script for extracting text from Gmail, LinkedIn, WhatsApp Web

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSelectedText') {
    const selectedText = window.getSelection().toString();
    
    if (selectedText.trim()) {
      sendResponse({ text: selectedText });
      return;
    }
    
    // Try to extract from Gmail
    const gmailBody = document.querySelector('[data-message-id]');
    if (gmailBody) {
      const text = gmailBody.innerText;
      sendResponse({ text });
      return;
    }
    
    // Try to extract from LinkedIn
    const linkedinPost = document.querySelector('[data-feed-item-id]');
    if (linkedinPost) {
      const text = linkedinPost.innerText;
      sendResponse({ text });
      return;
    }
    
    // Try to extract from WhatsApp Web
    const whatsappMessage = document.querySelector('[data-testid="msg-container"]');
    if (whatsappMessage) {
      const text = whatsappMessage.innerText;
      sendResponse({ text });
      return;
    }
    
    sendResponse({ text: '' });
  }
});

// Add context menu for "Check with JobTruth"
chrome.runtime.sendMessage({ action: 'setupContextMenu' });
