const API_URL = 'https://jobtruth-seven.vercel.app';

async function analyzeText(text) {
  try {
    const response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    return await response.json();
  } catch (e) {
    return { error: 'Could not connect to JobTruth' };
  }
}

function getSelectedText() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, { action: 'getSelectedText' }, (response) => {
        resolve(response?.text || '');
      });
    });
  });
}

function displayResult(result) {
  const content = document.getElementById('content');
  
  if (result.error) {
    content.innerHTML = `<div class="error">${result.error}</div>`;
    return;
  }
  
  if (!result.trust_score) {
    content.innerHTML = '<div class="error">No text selected. Please select a job offer message.</div>';
    return;
  }
  
  const riskClass = result.label === 'Looks Safe' ? 'safe' : result.label === 'Suspicious' ? 'suspicious' : 'risk';
  const flagsHtml = result.flags.map(f => 
    `<div style="font-size: 12px; margin: 4px 0; color: #5b6679;">
      <strong>${f.impact > 0 ? '+' : ''}${f.impact}</strong> ${f.reason}
    </div>`
  ).join('');
  
  content.innerHTML = `
    <div class="result ${riskClass}">
      <div class="label">${result.label}</div>
      <div class="score">${result.trust_score}/100</div>
      ${flagsHtml}
    </div>
  `;
}

async function init() {
  const text = await getSelectedText();
  
  if (!text.trim()) {
    document.getElementById('content').innerHTML = 
      '<div class="error">No text selected. Please select a job offer message in Gmail, LinkedIn, or WhatsApp Web.</div>';
    return;
  }
  
  const result = await analyzeText(text);
  displayResult(result);
}

function openFullApp() {
  chrome.tabs.create({ url: API_URL });
}

init();
