//Sean Hofer 2015
//there's not much in here, animations are all handled via CSS

$(function () {

  //keeps track of which header tab is active
  $('a.headItem').on('click', function () {
    var activeDiv = $("a.activeHeadItem").text();
    $("#" + activeDiv).removeClass('activeSubsection');

    $("a.activeHeadItem").removeClass('activeHeadItem');
    $(this).addClass('activeHeadItem');

    activeDiv = $(this).text();
    $("#" + activeDiv).addClass('activeSubsection');
  });

});