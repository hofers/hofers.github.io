window.dataLayer = window.dataLayer || []

function gtag () {
  dataLayer.push(arguments)
}

// Set up Google Analytics
gtag('js', new Date())

gtag('config', 'UA-143817336-1', {
  link_attribution: true
})

var c = function (url) {
  gtag('event', 'click', {
    event_category: 'outbound',
    event_label: url,
    transport_type: 'beacon',
  })
}

var d = function (url) {
  gtag('event', 'download', {
    event_category: 'download',
    event_label: url,
    transport_type: 'beacon',
  })
}

document.addEventListener('DOMContentLoaded', function () {
  // Add outbound link click event to all outbound links
  document.querySelectorAll("a[target='_blank']").forEach(a => {
    a.addEventListener('click', () => c(a.getAttribute('href')));
  });

  // Add download event to download links
  document.querySelectorAll("a[download]").forEach(a => {
    a.addEventListener('click', () => d(a.getAttribute('href')));
  });

  var tag = document.currentScript || document.scripts[1];
  tag.parentNode.removeChild(tag);
});