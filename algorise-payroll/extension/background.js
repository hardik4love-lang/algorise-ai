// Algorise PeopleOS — Background Service Worker (Manifest V3)
chrome.runtime.onInstalled.addListener(() => {
  console.log('Algorise PeopleOS Extension v2.4 installed');
  chrome.action.setBadgeText({ text: '481' });
  chrome.action.setBadgeBackgroundColor({ color: '#10b981' });
  chrome.alarms.create('syncTelemetry', { periodInMinutes: 1 });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'syncTelemetry') {
    chrome.action.setBadgeText({ text: '481' });
  }
});
