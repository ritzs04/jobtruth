// Background service worker for JobTruth extension

chrome.runtime.onInstalled.addListener(() => {
  console.log('JobTruth extension installed');
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'setupContextMenu') {
    chrome.contextMenus.create({
      id: 'jobtruth-check',
      title: 'Check with JobTruth',
      contexts: ['selection']
    });
  }
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'jobtruth-check') {
    chrome.tabs.sendMessage(tab.id, { action: 'getSelectedText' }, (response) => {
      if (response?.text) {
        chrome.storage.local.set({ selectedText: response.text });
        chrome.action.openPopup();
      }
    });
  }
});
