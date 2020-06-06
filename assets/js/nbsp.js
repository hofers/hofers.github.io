window.onload = () => {
  var paragraphs = document.getElementsByTagName("p");
  for (let p of paragraphs) {
    let html = p.innerHTML;
    p.innerHTML = html.substring(0,html.lastIndexOf(" ")) + "&nbsp;" + html.substring(html.lastIndexOf(" ")+1);
  }
};