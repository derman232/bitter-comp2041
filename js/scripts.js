$('document').ready(function(){
   // home page login boxes
   $( "#login-btn" ).click(function() {
     $( "#login-form" ).submit();
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
         window.location = "http://google.com/?gws_rd=ssl#q=" + $(this).val();
      });
   });

   // override enter key on maps search box
   $('#home_location').keydown(function(event) {
      if (event.keyCode == 13) {
         event.preventDefault();
      }
   });



});



