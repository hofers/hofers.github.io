// Sean Hofer 2015
// not much in here, animations are all handled via CSS
// I know I don't need jQuery but it's here because I like it okay?

$(function () {

  // keeps track of which header tab is active
  $('a.headItem').on('click', function () {
    var activeDiv = $("a.activeHeadItem").text();
    $("#" + activeDiv).removeClass('activeSubsection');

    $("a.activeHeadItem").removeClass('activeHeadItem');
    $(this).addClass('activeHeadItem');

    activeDiv = $(this).text();
    $("#" + activeDiv).addClass('activeSubsection');
  });

});