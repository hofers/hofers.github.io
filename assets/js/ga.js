window.dataLayer = window.dataLayer || []

function gtag () {
  dataLayer.push(arguments)
}

// Set up Google Analytics
gtag('js', new Date())

gtag('config', 'UA-143817336-1', {
  link_attribution: true
})

var trackClickEvent = function (url) {
  gtag('event', 'click', {
    event_category: 'outbound',
    event_label: url,
    transport_type: 'beacon',
    event_callback: function () {
      window.open(url);
    }
  })
}

var trackDownloadEvent = function (url) {
  gtag('event', 'download ', {
    event_category: 'download',
    event_label: url,
    transport_type: 'beacon',
  })
}

document.addEventListener('DOMContentLoaded', function () {
  // Add outbound link click event to all outbound links
  document.querySelectorAll("a[target='_blank']").forEach((e) => {
    e.addEventListener('click', (e) => { 
      trackClickEvent(e.getAttribute('href'));
      e.preventDefault();
    });
  });

  // Add download event to download links
  document.querySelectorAll("a[download]").forEach((e) => {
    e.addEventListener('click', (e) => { 
      trackDownloadEvent(e.getAttribute('href'));
    });
  });
});