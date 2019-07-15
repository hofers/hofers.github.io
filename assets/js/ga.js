window.dataLayer = window.dataLayer || [];

function gtag() {
  dataLayer.push(arguments);
}

gtag('js', new Date());

gtag('config', 'UA-143817336-1', {
  'link_attribution': true
});

var getOutboundLink = function (url) {
  gtag('event', 'click', {
    'event_category': 'outbound',
    'event_label': url,
    'transport_type': 'beacon',
    'event_callback': function () {
      document.location = url;
    }
  });
}

// Add outbound link click event to all outbound links
document.addEventListener("DOMContentLoaded", function (event) {
  document.querySelectorAll("a[target='_blank']").forEach((e) => {
    e.setAttribute("onclick", "getOutboundLink('" + e.getAttribute("href") + "');")
  });
});