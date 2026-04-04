$(function () {

  // ── Profile picture modal ────────────────────────────────────
  $('#profile-pic-wrap').on('click', function () {
    $('#profile-pic-modal').css('display', 'flex');
  });

  $('#profile-pic-modal').on('click', function () {
    $(this).hide();
  });

  $(document).on('keydown', function (e) {
    if (e.key === 'Escape') { $('#profile-pic-modal').hide(); }
  });

  // ── Business card session logic ───────────────────────────────
  function dismissCard() {
    $('#business-card').addClass('exit');
    setTimeout(function () { $('#card-overlay').addClass('fade-out'); }, 160);
    setTimeout(function () { $('#card-overlay').hide(); }, 680);
  }

  function showCard() {
    $('#business-card').removeClass('exit');
    $('#card-overlay').css({ display: 'flex', opacity: '' }).removeClass('fade-out');
  }

  if (!sessionStorage.getItem('card_shown')) {
    sessionStorage.setItem('card_shown', '1');
    $('#card-overlay').css('display', 'flex');
  }

  // ── Business card dismiss on click or ESC ────────────────────
  $('#card-overlay').on('click', function () { dismissCard(); });

  $(document).on('keydown', function (e) {
    if (e.key === 'Escape' && $('#card-overlay').is(':visible')) {
      dismissCard();
    }
  });

  // ── Sidebar card button ───────────────────────────────────────
  $(document).on('click', '#show-card-btn', function (e) {
    e.preventDefault();
    showCard();
  });

  // ── Initialise collapsed sections ────────────────────────────
  $('.section-header').each(function () {
    if ($(this).find('.toggle-icon').hasClass('collapsed')) {
      $(this).next('.section-body').hide();
    }
  });

  // ── Collapsible section toggle ────────────────────────────────
  $(document).on('click', '.section-header', function () {
    var $header = $(this);
    var $icon   = $header.find('.toggle-icon');
    var $body   = $header.next('.section-body');

    $icon.toggleClass('collapsed');
    $body.slideToggle(220);
  });

  // ── Publications: collapse overflow on load, toggle on click ────
  $('.pub-overflow').hide();
  // Hide year groups whose every publication is overflow (no visible entries)
  $('.pub-year-group').each(function () {
    if ($(this).find('.publication').not('.pub-overflow').length === 0) {
      $(this).hide();
    }
  });

  $(document).on('click', '.pub-show-all', function () {
    var $btn      = $(this);
    var $body     = $btn.closest('.section-body');
    var $overflow = $body.find('.pub-overflow');
    var $groups   = $body.find('.pub-year-group');
    var total     = $btn.data('total');
    var expanded  = $btn.data('expanded');

    if (expanded) {
      $overflow.slideUp(200);
      // Re-hide year groups that become empty after collapsing
      setTimeout(function () {
        $groups.each(function () {
          if ($(this).find('.publication').not('.pub-overflow').length === 0) {
            $(this).hide();
          }
        });
      }, 210);
      $btn.text('Show all ' + total + ' \u25be');
      $btn.data('expanded', false);
    } else {
      $groups.show();
      $overflow.slideDown(200);
      $btn.text('Show fewer \u25b4');
      $btn.data('expanded', true);
    }
  });

  // ── BibTeX open in new tab ───────────────────────────────────
  $(document).on('click', '.pub-bib-link', function () {
    var bib  = $(this).data('bib');
    var key  = $(this).data('bib-key');
    var blob = new Blob([bib], { type: 'text/plain;charset=utf-8' });
    var url  = URL.createObjectURL(blob);
    var win  = window.open(url, '_blank');
    if (win) {
      win.addEventListener('load', function () { win.document.title = key; });
    }
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
