$(function () {

  // ── Business card → main page reveal ─────────────────────────
  $('#card-overlay').on('click', function () {
    $('#business-card').addClass('exit');

    // Start fading the overlay background slightly after the card starts rotating
    setTimeout(function () {
      $('#card-overlay').addClass('fade-out');
    }, 160);

    setTimeout(function () {
      $('#card-overlay').hide();
      $('#main-page').removeClass('hidden').hide().fadeIn(400);
    }, 680);
  });

  // ── Collapsible section toggle ────────────────────────────────
  $(document).on('click', '.section-header', function () {
    var $header = $(this);
    var $icon   = $header.find('.toggle-icon');
    var $body   = $header.next('.section-body');

    $icon.toggleClass('collapsed');
    $body.slideToggle(220);
  });

  // ── Side panel smooth scroll ──────────────────────────────────
  $(document).on('click', '.panel-nav a', function (e) {
    e.preventDefault();
    var $target = $($(this).attr('href'));
    if ($target.length) {
      $('html, body').animate({ scrollTop: $target.offset().top - 48 }, 360);
    }
  });

});
