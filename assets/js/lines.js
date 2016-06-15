$(function drawLines() {
  d3.select("svg").remove();
  var lineData = [];
  var color = "blue";

  var svgContainer = d3.select("#home").append("svg")
  
  for (var i = 0; i < 8; i++) {
    lineData = [{
      "x": window.innerWidth * (i % 2),
      "y": Math.random() * window.innerHeight
    }];
    color = "#a8000e";
    for (var j = 0; j < 6; j++) {
      lineData.push({
        "x": Math.random() * window.innerWidth,
        "y": Math.random() * window.innerHeight
      })
    }
    var lineFunction = d3.svg.line()
      .x(function(d) {
        return d.x;
      })
      .y(function(d) {
        return d.y;
      })
      .interpolate("step-after");

    var lineGraph = svgContainer.append("path")
      .attr("d", lineFunction(lineData))
      .attr("stroke", color)
      .attr("stroke-width", 1)
      .attr("class", "path")
      .attr("fill", "none");
  }

  window.onresize = d3.select("svg").remove;
  window.onresize = drawLines;




});
