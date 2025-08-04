// Регулярное выражение для проверки YouTube-ссылок
const YOUTUBE_REGEX = /^https:\/\/(www\.)?youtu\.?be(\.com|\.ru)?/;

// Создаём пункты в контекстном меню
chrome.runtime.onInstalled.addListener(() => {
  // Пункт для высокого качества
  chrome.contextMenus.create({
    id: "downloadHighQuality",
    title: "Скачать видео в высоком качестве",
    contexts: ["link"],
    documentUrlPatterns: ["*://*/*"],
    targetUrlPatterns: ["*://*.youtube.com/*", "*://*.youtu.be/*", "*://*.youtube.ru/*"]
  });

  // Пункт для низкого качества
  chrome.contextMenus.create({
    id: "downloadLowQuality",
    title: "Скачать видео в низком качестве",
    contexts: ["link"],
    documentUrlPatterns: ["*://*/*"],
    targetUrlPatterns: ["*://*.youtube.com/*", "*://*.youtu.be/*", "*://*.youtube.ru/*"]
  });

  // Пункт для аудио
  chrome.contextMenus.create({
    id: "downloadAudio",
    title: "Скачать как аудио",
    contexts: ["link"],
    documentUrlPatterns: ["*://*/*"],
    targetUrlPatterns: ["*://*.youtube.com/*", "*://*.youtu.be/*", "*://*.youtube.ru/*"]
  });
});

// Обработчик выбора пункта меню
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!info.linkUrl || !YOUTUBE_REGEX.test(info.linkUrl)) {
    return;
  }

  let action;
  switch (info.menuItemId) {
    case "downloadHighQuality":
      action = "high_quality";
      break;
    case "downloadLowQuality":
      action = "low_quality";
      break;
    case "downloadAudio":
      action = "audio";
      break;
    default:
      return;
  }

  // Отправляем данные в Python-приложение
  sendToNativeApp({
    url: info.linkUrl,
    action: action
  });
});

function sendToNativeApp(data) {
  const nativeAppName = "youtube_downloader";
  
  chrome.runtime.sendNativeMessage(nativeAppName, data,
    function(response) {
      if (chrome.runtime.lastError) {
        console.error("Ошибка:", chrome.runtime.lastError);
      } else {
        console.log("Получен ответ:", response);
      }
    }
  );
}