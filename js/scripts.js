$('document').ready(function(){
   // home page login boxes
   $( "#login-btn" ).click(function() {
     $( "#login-form" ).submit();
   });

   // delete and suspension button confirmation
   $( "#suspend-btn" ).click(function() {
      event.preventDefault();
      if ($(this).text() != 'Loading...') {
         if (confirm('Are you sure you want to suspend your account?')) {
            $(this).text('Loading...');
            window.location.href = "?page=suspend_acc";
         } else {
            $(this).text('Suspend Your Account');
         }
      }

   });
   $( "#delete-acc-btn" ).click(function() {
      event.preventDefault();
      if ($(this).text() != 'Loading...') {
         if (confirm('Are you sure you want to DELETE your account? This action cannot be undone.')) {
            $(this).text('Loading...');
            window.location.href = "?page=delete_acc";
         } else {
            $(this).text('Delete Your Account');
         }
      }
   });


   // hide / show feed page new tweet box
   $( "textarea#new-tweet" ).focusin(function() {
      $(this).attr("rows", "3");
      $(".tweet-submit").show();
   });
   $( "textarea#new-tweet" ).focusout(function() {
      if ( !$(this).val() ) {
         $(this).attr("rows", "1");
         $(".tweet-submit").hide();
      }
   });

   // tweet box counter
   $('textarea#new-tweet').bind('input propertychange', function() {
      $(".char-count").html(140 - $("textarea#new-tweet").val().length);
   });

   // link for individual tweets
   $('.tweet-body-selector').on("click", ":not(a img)", function() {
      $(this).find('#bleat_id').each(function(){
         window.location.href = "?page=bleat_page&bleat_id=" + $(this).val();
      });
   });

   // override enter key on maps search box
   $('#home_location').keydown(function(event) {
      if (event.keyCode == 13) {
         event.preventDefault();
      }
   });

   $('#location-btn').on("click", function() {
      // adapted from https://developers.google.com/web/fundamentals/native-hardware/user-location/obtain-location?hl=en
      event.preventDefault();
      if ($(this).text() == 'Remove Location') {
          $('#tweet-lat').val('');
          $('#tweet-long').val('');
          $('#location-btn').text('Add Location');
      } else if (navigator.geolocation) {
       $('#location-btn').text('Adding Location...');
        var startPos;
        var geoOptions = {
           timeout: 10 * 1000
        }

        var geoSuccess = function(position) {
          startPos = position;
          $('#tweet-lat').val(startPos.coords.latitude);
          $('#tweet-long').val(startPos.coords.longitude);
          $('#location-btn').text('Remove Location');
        };
        var geoError = function(error) {
          $('#location-btn').text('Add Location');
          alert('Unable to retrieve location. Error code: ' + error.code);
        };

        navigator.geolocation.getCurrentPosition(geoSuccess, geoError, geoOptions);
     }
   });

   $('.btn-load').on("click", function() {
      if ($(this).text() == 'Loading...') {
         event.preventDefault();  // not a complete fix... but its a start
                                  // doesn't handle locations where button's are just wrapped within links
      }
      $(this).text('Loading...');
   });

   $(function () {
     $('[data-toggle="tooltip"]').tooltip()
   });

   $(function () {
      initAutocomplete()
   });

});



