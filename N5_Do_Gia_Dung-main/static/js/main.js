// Ảnh header trượt liên tục đã xử lý trong CSS với animation
$(function () {
  // Smooth scroll đến các section
  $("#right-menu a, .navbar-nav .nav-link[href^='#']").on(
    "click",
    function (e) {
      var target = $($(this).attr("href"));
      if (target.length) {
        e.preventDefault();
        $("html, body").animate({ scrollTop: target.offset().top - 70 }, 500);
      }
    }
  );
});
