
$.fn.modalForm = function (options) {
  var _this = this;

  function disableButton($el) {
    var replacement = $el.data('disable-with');
    if (replacement !== undefined) {
      $el.data('enable-with', $el.html());
      $el.html(replacement);
    }
    $el.attr('disabled', true);

    $el.bind('click.disabledButton', function (e) {
      e.stopImmediatePropagation();
      return false;
    });
  }

  function enableButton($el) {
    var replacement = $el.data('enable-with');
    if (replacement !== undefined) {
      $el.html(replacement);
    }
    $el.attr('disabled', false);
    $el.unbind('click.disabledButton');
  }

  function displayError(message) {
    $('.extra-errors', _this).html(
      '<div class="alert alert-danger" role="alert">' +
      message +
      '</div>'
    );
  }

  $(this).on('submit', 'form', function (e) {
    e.preventDefault();

    var $submit = $('button[type="submit"]', _this);

    disableButton($submit);

    $.ajax({
      type: 'POST',
      url: $(this).attr('action'),
      data: $(this).serialize(),
      dataType: 'json'
    }).done(function (data) {
      if (data.data) {
        $('.modal-body', _this).html(data.data);
      } else if (data.redirect) {
        window.location.replace(data.redirect);
      } else {
        displayError('Request failed. Please try again later.');
      }
    }).fail(function (jqXHR, textStatus, errorThrown) {
      displayError([errorThrown, 'Please try again later.'].join('<br/>'));
      enableButton($submit);
    });
  });

  return this;
};

function getNextUrl() {
  var next = $('.login-wrapper form input[name=next]').val();
  if (!next) {
    next = window.location.pathname;
  }
  return next;
}

$(document).ready(function () {
  $('.signup-show').click(function(e) {

    var next = getNextUrl();
    if (next !== undefined) {
      $('#signupModal form input[name=next]').val(next);
    }

    e.preventDefault();
    $('#signupModal').modal();
  });

  $('#signupModal').modalForm();
});
